"""手机钥匙（App 的 Secure Enclave P-256 钥匙）面容打卡接口。"""

import base64
import hashlib
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

import frappe
from frappe.utils.password import set_encrypted_password, update_password

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import device_key
from hrms.api.checkin_service import AUDIT_TITLES, create_checkin
from hrms.api.passkey_webauthn import store_challenge
from hrms.tests.test_passkey_api import ensure_location
from hrms.tests.utils import HRMSTestSuite
from hrms.utils import attendance_beacon, mobile_attendance
from hrms.utils.attendance_beacon import beacon_code, ble_checkin_enabled_for

API_USER = "device-key-api@example.com"
OTHER_USER = "device-key-api-other@example.com"
PASSWORD = "Device-Key-Test-Pass-1"
OFFICE_IP = "203.0.113.5"
MOBILE_IP = "198.51.100.1"
# 公开的测试向量密钥，不是任何真实密钥；固定的时刻落在时间段 179220602
BEACON_TEST_KEY = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
BEACON_NOW = 1792206020
BEACON_SLOT = 179220602
BEACON_LOG_TITLE = "Checkin Beacon Rejected"
# 打卡点在 (35.6812, 139.7671)，半径 200 米
NEAR = (35.6813, 139.7672)


def b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class PhoneKey:
	"""App 里的手机钥匙：P-256，公钥是 X9.63 未压缩点，签名是 DER。"""

	def __init__(self):
		self.private_key = ec.generate_private_key(ec.SECP256R1())
		self.raw_public_key = self.private_key.public_key().public_bytes(
			serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
		)
		self.public_key = b64url(self.raw_public_key)
		self.key_id = b64url(hashlib.sha256(self.raw_public_key).digest())

	def sign(self, purpose: str, challenge: str) -> str:
		message = f"uohr-device-key:{purpose}:{challenge}".encode()
		return b64url(self.private_key.sign(message, ec.ECDSA(hashes.SHA256())))


class DeviceKeyTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(API_USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for user in (API_USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
			update_password(user, PASSWORD)
			frappe.cache.delete_value([device_key._failure_key(user), device_key._lock_key(user)])
		frappe.db.delete("Device Checkin Key", {"user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("PWA Notification", {"to_user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("Employee Checkin", {"employee": ("in", [self.employee, self.other_employee])})
		self.location = ensure_location()
		settings = frappe.get_doc("HR Settings")
		settings.passkey_checkin_location = self.location
		settings.passkey_checkin_enabled_for_all = 0
		settings.set("passkey_checkin_pilot_employees", [{"employee": self.employee}])
		settings.qr_checkin_allowed_ips = "203.0.113.0/24"
		settings.ble_checkin_enabled = 1
		settings.save()
		self.setup_beacon()

	def setup_beacon(self):
		"""签到牌蓝牙码：测试打卡点用测试向量密钥，时间固定在向量那一刻（用例结束时一并回滚）。"""
		set_encrypted_password("QR Checkin Location", self.location, BEACON_TEST_KEY, "ble_key")
		clock = patch.object(attendance_beacon, "_now", return_value=BEACON_NOW)
		clock.start()
		self.addCleanup(clock.stop)
		# 失败计数在 Redis 里不会回滚，前后都清掉，免得用例之间串数
		self.clear_rejection_counter()
		self.addCleanup(self.clear_rejection_counter)
		frappe.db.delete("Error Log", {"method": BEACON_LOG_TITLE})

	def clear_rejection_counter(self):
		frappe.cache.delete_value(f"hrms:checkin-beacon-rejections:{API_USER}")

	@property
	def beacon(self):
		"""此刻有效的蓝牙码（按当前打卡点算出，和向量用同一把密钥）。"""
		return {
			"beacon_slot": BEACON_SLOT,
			"beacon_code": beacon_code(BEACON_TEST_KEY, self.location, BEACON_SLOT),
		}

	@property
	def wrong_beacon(self):
		code = self.beacon["beacon_code"]
		return {"beacon_slot": BEACON_SLOT, "beacon_code": code[:-1] + ("0" if code[-1] != "0" else "1")}

	def rejections(self):
		"""被拒记录；查完回到原来的登录用户，不打断用例里接着的打卡调用。"""
		user = frappe.session.user
		frappe.set_user("Administrator")
		try:
			return frappe.get_all(
				"Error Log",
				filters={"method": BEACON_LOG_TITLE},
				fields=["method", "error"],
				order_by="creation",
			)
		finally:
			frappe.set_user(user)

	def begin_recording(self, key_id, **position):
		"""开始打卡，并返回存进验证码记录的内容（记录在 complete 时才被消耗）。"""
		with patch.object(device_key, "store_challenge", wraps=device_key.store_challenge) as stored:
			begin = self.begin(key_id, **position)
		return begin, stored.call_args.args[2] if stored.called else None

	def audit_message(self):
		return frappe.db.get_value(
			"Error Log",
			{"method": "Device Key Checkin Audit - IN", "error": ("like", f"%{self.employee}%")},
			"error",
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		# 回滚这条用例的改动：测试跑完 Frappe 会提交一次，不回滚的话 HR 设置等会留在共用的开发站点上
		super().tearDown()

	def register(self, user=API_USER, key=None, replaces=None, device_name="iPhone (iPhone16,2)"):
		key = key or PhoneKey()
		frappe.set_user(user)
		start = device_key.register_options(password=PASSWORD, replaces_key_id=replaces)
		self.assertEqual(start["status"], "ok")
		result = device_key.register_complete(
			challenge=start["challenge"],
			public_key=key.public_key,
			signature=key.sign("register", start["challenge"]),
			device_name=device_name,
		)
		frappe.set_user("Administrator")
		self.assertEqual(result, {"status": "ok", "key_id": key.key_id})
		return key

	def begin(self, key_id, ip=OFFICE_IP, log_type="IN", **position):
		with patch.object(device_key, "get_client_ip", return_value=ip):
			return device_key.begin_checkin(log_type=log_type, key_id=key_id, **position)

	def complete(self, key, challenge, key_id=None, purpose="checkin"):
		with patch("frappe.publish_realtime"):
			return device_key.complete_checkin(
				challenge=challenge, key_id=key_id or key.key_id, signature=key.sign(purpose, challenge)
			)

	def key_ids(self, user=API_USER):
		return sorted(frappe.get_all("Device Checkin Key", filters={"user": user}, pluck="key_id"))

	def checkins(self):
		return frappe.db.count("Employee Checkin", {"employee": self.employee})


class TestDeviceKeyAccess(DeviceKeyTestCase):
	def test_guest_and_users_without_employee_are_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			device_key.get_checkin_context()
		frappe.set_user("Administrator")
		with self.assertRaises(frappe.PermissionError):
			device_key.begin_checkin(log_type="IN", key_id="x")
		frappe.db.set_value("Employee", self.other_employee, "status", "Left")
		frappe.set_user(OTHER_USER)
		with self.assertRaisesRegex(frappe.ValidationError, "not linked to an employee"):
			device_key.register_options(password=PASSWORD)

	def test_http_methods(self):
		self.assertIn("GET", frappe.allowed_http_methods_for_whitelisted_func[device_key.get_checkin_context])
		self.assertNotIn(
			"POST", frappe.allowed_http_methods_for_whitelisted_func[device_key.get_checkin_context]
		)
		for fn in (
			device_key.register_options,
			device_key.register_complete,
			device_key.begin_checkin,
			device_key.complete_checkin,
		):
			self.assertEqual(
				tuple(frappe.allowed_http_methods_for_whitelisted_func[fn]), ("POST",), fn.__name__
			)


class TestDeviceKeyContext(DeviceKeyTestCase):
	def test_context_for_pilot_and_non_pilot(self):
		self.register()
		frappe.set_user(API_USER)
		with patch.object(device_key, "get_client_ip", return_value=OFFICE_IP):
			context = device_key.get_checkin_context()
		self.assertEqual(
			context,
			{
				"enabled": True,
				"on_office_network": True,
				"location": {
					"name": self.location,
					"description": frappe.db.get_value("QR Checkin Location", self.location, "description")
					or self.location,
				},
				"key_count": 1,
				"ble_checkin": True,
			},
		)
		frappe.set_user(OTHER_USER)
		with patch.object(device_key, "get_client_ip", return_value=OFFICE_IP):
			context = device_key.get_checkin_context()
		self.assertEqual(
			context,
			{
				"enabled": False,
				"on_office_network": False,
				"location": None,
				"key_count": 0,
				"ble_checkin": False,
			},
		)

	def test_context_reports_ble(self):
		frappe.set_user(API_USER)
		with patch.object(device_key, "get_client_ip", return_value=MOBILE_IP):
			self.assertIs(device_key.get_checkin_context()["ble_checkin"], True)
			frappe.set_user("Administrator")
			frappe.db.set_single_value("HR Settings", "ble_checkin_enabled", 0)
			frappe.set_user(API_USER)
			self.assertIs(device_key.get_checkin_context()["ble_checkin"], False)

	def test_key_count_ignores_passkeys(self):
		frappe.get_doc(
			{
				"doctype": "Passkey Credential",
				"user": API_USER,
				"employee": self.employee,
				"credential_id": "device-key-test-passkey",
				"public_key": "x",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(API_USER)
		with patch.object(device_key, "get_client_ip", return_value=MOBILE_IP):
			context = device_key.get_checkin_context()
		self.assertEqual((context["key_count"], context["on_office_network"]), (0, False))


class TestDeviceKeyRegistration(DeviceKeyTestCase):
	def test_register_options_ok(self):
		frappe.set_user(API_USER)
		start = device_key.register_options(password=PASSWORD)
		self.assertEqual(set(start), {"status", "challenge", "timeout"})
		self.assertEqual((start["status"], start["timeout"]), ("ok", 300000))
		self.assertGreaterEqual(len(start["challenge"]), 43)

	def test_register_stores_key_and_notifies_every_time(self):
		key = self.register()
		row = frappe.db.get_value(
			"Device Checkin Key",
			{"key_id": key.key_id},
			["user", "employee", "public_key", "device_name", "last_used"],
			as_dict=True,
		)
		self.assertEqual(
			(row.user, row.employee, row.public_key, row.device_name, row.last_used),
			(API_USER, self.employee, key.public_key, "iPhone (iPhone16,2)", None),
		)
		notifications = frappe.get_all(
			"PWA Notification", filters={"to_user": API_USER}, fields=["notification_title", "message"]
		)
		self.assertEqual(len(notifications), 1)
		self.assertIn("iPhone (iPhone16,2)", notifications[0].message)
		self.assertIn(frappe.utils.now_datetime().strftime("%Y-%m-%d"), notifications[0].message)
		self.assertIn("心当たりがない場合は HR に連絡してください", notifications[0].message)
		self.assertTrue(notifications[0].notification_title)
		self.register()
		self.assertEqual(frappe.db.count("PWA Notification", {"to_user": API_USER}), 2)

	def test_device_name_is_shown_as_text(self):
		self.register(device_name='<img src=x onerror="alert(1)">')
		message = frappe.db.get_value("PWA Notification", {"to_user": API_USER}, "message")
		self.assertNotIn("<img", message)
		self.assertIn("&lt;img", message)

	def test_wrong_password(self):
		frappe.set_user(API_USER)
		self.assertEqual(device_key.register_options(password="wrong"), {"status": "wrong_password"})
		self.assertEqual(device_key.register_options(password=""), {"status": "wrong_password"})

	def test_five_wrong_passwords_lock_registration_for_ten_minutes(self):
		frappe.set_user(API_USER)
		for _ in range(4):
			self.assertEqual(device_key.register_options(password="wrong")["status"], "wrong_password")
		self.assertEqual(device_key.register_options(password="wrong"), {"status": "too_many_attempts"})
		# 暂停期间输对也不行
		self.assertEqual(device_key.register_options(password=PASSWORD), {"status": "too_many_attempts"})
		ttl = frappe.cache.ttl(frappe.cache.make_key(device_key._lock_key(API_USER)))
		self.assertTrue(590 <= ttl <= 600, ttl)
		# 只锁这个账号
		frappe.set_user(OTHER_USER)
		self.assertEqual(device_key.register_options(password=PASSWORD)["status"], "ok")
		# 10 分钟后（锁过期）恢复
		frappe.cache.delete_value(device_key._lock_key(API_USER))
		frappe.set_user(API_USER)
		self.assertEqual(device_key.register_options(password=PASSWORD)["status"], "ok")

	def test_failure_window_is_ten_minutes_and_success_resets_it(self):
		frappe.set_user(API_USER)
		for _ in range(4):
			device_key.register_options(password="wrong")
		ttl = frappe.cache.ttl(frappe.cache.make_key(device_key._failure_key(API_USER)))
		self.assertTrue(590 <= ttl <= 600, ttl)
		self.assertEqual(device_key.register_options(password=PASSWORD)["status"], "ok")
		for _ in range(4):
			self.assertEqual(device_key.register_options(password="wrong")["status"], "wrong_password")

	def test_wrong_password_does_not_touch_login_lockout(self):
		frappe.cache.hset("login_failed_count", API_USER, 2)
		frappe.set_user(API_USER)
		device_key.register_options(password="wrong")
		device_key.register_options(password=PASSWORD)
		self.assertEqual(frappe.cache.hget("login_failed_count", API_USER), 2)
		frappe.cache.hdel("login_failed_count", API_USER)

	def test_device_limit(self):
		for _ in range(3):
			self.register()
		frappe.set_user(API_USER)
		self.assertEqual(device_key.register_options(password=PASSWORD), {"status": "device_limit"})
		# 密码错时先报密码
		self.assertEqual(device_key.register_options(password="wrong"), {"status": "wrong_password"})

	def test_limit_is_per_user_and_separate_from_passkeys(self):
		for _ in range(3):
			self.register(user=OTHER_USER)
		for i in range(3):
			frappe.get_doc(
				{
					"doctype": "Passkey Credential",
					"user": API_USER,
					"employee": self.employee,
					"credential_id": f"device-key-test-passkey-{i}",
					"public_key": "x",
				}
			).insert(ignore_permissions=True)
		self.register()

	def test_limit_is_checked_again_when_completing(self):
		self.register()
		self.register()
		frappe.set_user(API_USER)
		starts = [device_key.register_options(password=PASSWORD) for _ in range(2)]
		keys = [PhoneKey(), PhoneKey()]
		args = [
			{
				"challenge": start["challenge"],
				"public_key": key.public_key,
				"signature": key.sign("register", start["challenge"]),
				"device_name": "iPhone",
			}
			for start, key in zip(starts, keys, strict=True)
		]
		device_key.register_complete(**args[0])
		with self.assertRaisesRegex(frappe.ValidationError, "3 devices"):
			device_key.register_complete(**args[1])
		frappe.set_user("Administrator")
		self.assertEqual(len(self.key_ids()), 3)

	def test_same_public_key_cannot_be_registered_twice(self):
		key = self.register()
		for user in (API_USER, OTHER_USER):
			frappe.set_user(user)
			start = device_key.register_options(password=PASSWORD)
			with self.assertRaises(frappe.ValidationError):
				device_key.register_complete(
					challenge=start["challenge"],
					public_key=key.public_key,
					signature=key.sign("register", start["challenge"]),
					device_name="iPhone",
				)
		frappe.set_user("Administrator")
		self.assertEqual((self.key_ids(), self.key_ids(OTHER_USER)), ([key.key_id], []))

	def test_password_checks_are_claimed_before_checking(self):
		# 模拟并发：5 次尝试已经占了名额、还没核对完，第 6 个请求不再核对密码
		for _ in range(5):
			device_key._claim_password_attempt(API_USER)
		frappe.set_user(API_USER)
		with patch.object(device_key, "check_password") as check:
			self.assertEqual(device_key.register_options(password=PASSWORD), {"status": "too_many_attempts"})
		check.assert_not_called()

	def test_replacement_does_not_use_a_slot(self):
		keys = [self.register() for _ in range(3)]
		new_key = self.register(replaces=keys[0].key_id)
		self.assertEqual(self.key_ids(), sorted([keys[1].key_id, keys[2].key_id, new_key.key_id]))
		self.assertEqual(frappe.db.count("PWA Notification", {"to_user": API_USER}), 4)

	def test_replacing_someone_elses_key_is_ignored(self):
		other = self.register(user=OTHER_USER)
		for _ in range(3):
			self.register()
		frappe.set_user(API_USER)
		self.assertEqual(
			device_key.register_options(password=PASSWORD, replaces_key_id=other.key_id),
			{"status": "device_limit"},
		)
		frappe.set_user("Administrator")
		self.assertEqual(self.key_ids(OTHER_USER), [other.key_id])
		# 名额没满时也不会删掉别人的钥匙
		frappe.db.delete("Device Checkin Key", {"user": API_USER})
		self.register(replaces=other.key_id)
		self.assertEqual(self.key_ids(OTHER_USER), [other.key_id])

	def test_register_rejects_bad_signature(self):
		key, wrong_key = PhoneKey(), PhoneKey()
		frappe.set_user(API_USER)
		start = device_key.register_options(password=PASSWORD)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(
				challenge=start["challenge"],
				public_key=key.public_key,
				signature=wrong_key.sign("register", start["challenge"]),
				device_name="iPhone",
			)
		self.assertEqual(self.key_ids(), [])
		self.assertFalse(frappe.db.exists("PWA Notification", {"to_user": API_USER}))

	def test_register_signature_is_bound_to_purpose(self):
		key = PhoneKey()
		frappe.set_user(API_USER)
		start = device_key.register_options(password=PASSWORD)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(
				challenge=start["challenge"],
				public_key=key.public_key,
				signature=key.sign("checkin", start["challenge"]),
				device_name="iPhone",
			)

	def test_register_rejects_malformed_key_or_signature(self):
		key = PhoneKey()
		compressed = b64url(
			key.private_key.public_key().public_bytes(
				serialization.Encoding.X962, serialization.PublicFormat.CompressedPoint
			)
		)
		for public_key, signature in (
			(compressed, None),
			("not base64 !", None),
			(b64url(b"\x04" + b"\x00" * 64), None),
			(key.public_key, "not-a-signature"),
			(key.public_key, ""),
		):
			frappe.set_user(API_USER)
			start = device_key.register_options(password=PASSWORD)
			with self.assertRaises(frappe.ValidationError, msg=public_key):
				device_key.register_complete(
					challenge=start["challenge"],
					public_key=public_key,
					signature=signature
					if signature is not None
					else key.sign("register", start["challenge"]),
					device_name="iPhone",
				)
		self.assertEqual(self.key_ids(), [])

	def test_register_challenge_is_single_use(self):
		key = PhoneKey()
		frappe.set_user(API_USER)
		start = device_key.register_options(password=PASSWORD)
		args = {
			"challenge": start["challenge"],
			"public_key": key.public_key,
			"signature": key.sign("register", start["challenge"]),
			"device_name": "iPhone",
		}
		device_key.register_complete(**args)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(**args)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(**{**args, "challenge": "unknown"})

	def test_register_challenge_of_another_user_is_rejected(self):
		key = PhoneKey()
		frappe.set_user(OTHER_USER)
		start = device_key.register_options(password=PASSWORD)
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(
				challenge=start["challenge"],
				public_key=key.public_key,
				signature=key.sign("register", start["challenge"]),
				device_name="iPhone",
			)
		frappe.set_user("Administrator")
		self.assertEqual(self.key_ids() + self.key_ids(OTHER_USER), [])

	def test_register_needs_a_password_checked_challenge(self):
		key = PhoneKey()
		for record in ({"user": API_USER}, {"user": API_USER, "password_verified": False}):
			challenge = store_challenge(
				device_key.PURPOSE_REGISTER, b"0" * 32 + str(record).encode(), record, 60
			)
			frappe.set_user(API_USER)
			with self.assertRaises(frappe.ValidationError):
				device_key.register_complete(
					challenge=challenge,
					public_key=key.public_key,
					signature=key.sign("register", challenge),
					device_name="iPhone",
				)
		# 通行密钥的登记验证码不能拿来登记手机钥匙
		challenge = store_challenge("register", b"1" * 32, {"user": API_USER, "password_verified": True}, 60)
		with self.assertRaises(frappe.ValidationError):
			device_key.register_complete(
				challenge=challenge,
				public_key=key.public_key,
				signature=key.sign("register", challenge),
				device_name="iPhone",
			)
		self.assertEqual(self.key_ids(), [])


class TestDeviceKeyCheckin(DeviceKeyTestCase):
	def test_office_network_checkin(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id)
		self.assertEqual(set(begin), {"status", "challenge", "evidence"})
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "office_network"))
		result = self.complete(key, begin["challenge"])
		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			"Employee Checkin",
			{"employee": self.employee},
			["name", "log_type", "time", "device_id", "checkin_method", "latitude"],
			as_dict=True,
		)
		self.assertEqual(
			result,
			{
				"status": "ok",
				"log_type": "IN",
				"time": str(row.time),
				"employee": self.employee,
				"employee_name": frappe.db.get_value("Employee", self.employee, "employee_name"),
				"location": self.location,
				"evidence": "office_network",
			},
		)
		self.assertEqual(
			(row.device_id, row.checkin_method, row.latitude or None), (self.location, "Device Key", None)
		)
		self.assertTrue(frappe.db.get_value("Device Checkin Key", {"key_id": key.key_id}, "last_used"))
		self.assertTrue(
			frappe.db.exists(
				"Error Log",
				{"method": "Device Key Checkin Audit - IN", "error": ("like", f"%{self.employee}%")},
			)
		)

	def test_mobile_data_needs_location_then_uses_gps(self):
		key = self.register()
		frappe.set_user(API_USER)
		self.assertEqual(self.begin(key.key_id, ip=MOBILE_IP), {"status": "need_location", "reason": None})
		begin = self.begin(key.key_id, ip=MOBILE_IP, latitude=35.6813, longitude=139.7672, accuracy=30)
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "gps"))
		result = self.complete(key, begin["challenge"])
		self.assertEqual(result["evidence"], "gps")
		frappe.set_user("Administrator")
		latitude = frappe.db.get_value("Employee Checkin", {"employee": self.employee}, "latitude")
		self.assertAlmostEqual(latitude, 35.6813, places=4)

	def test_far_away_is_presence_unconfirmed(self):
		key = self.register()
		frappe.set_user(API_USER)
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, latitude=35.75, longitude=139.9, accuracy=10),
			{"status": "presence_unconfirmed", "reason": "too_far"},
		)

	def test_disabled_comes_before_presence_and_key(self):
		frappe.set_user(OTHER_USER)
		self.assertEqual(self.begin("missing", ip=MOBILE_IP), {"status": "disabled"})
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "passkey_checkin_location", None)
		frappe.set_user(API_USER)
		self.assertEqual(self.begin("missing"), {"status": "disabled"})

	def test_presence_comes_before_key(self):
		frappe.set_user(API_USER)
		self.assertEqual(self.begin("missing", ip=MOBILE_IP)["status"], "need_location")

	def test_unknown_or_foreign_key_is_no_device_key(self):
		other = self.register(user=OTHER_USER)
		frappe.set_user(API_USER)
		self.assertEqual(self.begin("missing"), {"status": "no_device_key"})
		self.assertEqual(self.begin(other.key_id), {"status": "no_device_key"})
		self.assertEqual(self.begin(""), {"status": "no_device_key"})

	def test_key_deleted_by_hr_is_no_device_key(self):
		key = self.register()
		frappe.delete_doc(
			"Device Checkin Key", frappe.db.get_value("Device Checkin Key", {"key_id": key.key_id})
		)
		frappe.set_user(API_USER)
		self.assertEqual(self.begin(key.key_id), {"status": "no_device_key"})

	def test_invalid_log_type(self):
		key = self.register()
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			self.begin(key.key_id, log_type="SIDEWAYS")

	def test_cooldown_blocks_begin(self):
		key = self.register()
		frappe.set_user(API_USER)
		self.complete(key, self.begin(key.key_id)["challenge"])
		with self.assertRaisesRegex(frappe.ValidationError, "within the last 5 minutes"):
			self.begin(key.key_id)

	def test_complete_rechecks_cooldown(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id)
		frappe.set_user("Administrator")
		with patch("frappe.publish_realtime"):
			create_checkin(employee=self.employee, log_type="IN", location=self.location, method="QR")
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			self.complete(key, begin["challenge"])
		self.assertEqual(self.checkins(), 1)

	def test_bad_signature_is_rejected(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id)
		with self.assertRaises(frappe.ValidationError):
			self.complete(PhoneKey(), begin["challenge"], key_id=key.key_id)
		with self.assertRaises(frappe.ValidationError):
			self.complete(key, self.begin(key.key_id)["challenge"], purpose="register")
		with patch("frappe.publish_realtime"), self.assertRaises(frappe.ValidationError):
			device_key.complete_checkin(
				challenge=self.begin(key.key_id)["challenge"], key_id=key.key_id, signature="%%%"
			)
		self.assertEqual(self.checkins(), 0)
		self.assertIsNone(frappe.db.get_value("Device Checkin Key", {"key_id": key.key_id}, "last_used"))

	def test_challenge_cannot_be_replayed(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id)
		signature = key.sign("checkin", begin["challenge"])
		with patch("frappe.publish_realtime"):
			device_key.complete_checkin(challenge=begin["challenge"], key_id=key.key_id, signature=signature)
			with self.assertRaises(frappe.ValidationError):
				device_key.complete_checkin(
					challenge=begin["challenge"], key_id=key.key_id, signature=signature
				)
		self.assertEqual(self.checkins(), 1)

	def test_complete_must_use_the_key_given_to_begin(self):
		first, second = self.register(), self.register()
		frappe.set_user(API_USER)
		begin = self.begin(first.key_id)
		with self.assertRaises(frappe.ValidationError):
			self.complete(second, begin["challenge"])
		self.assertEqual(self.checkins(), 0)

	def test_other_account_cannot_use_my_key_or_challenge(self):
		mine = self.register()
		other = self.register(user=OTHER_USER)
		frappe.set_user(API_USER)
		begin = self.begin(mine.key_id)
		# 别人拿到我的验证码，用他自己的钥匙或我的 key_id 都不行
		frappe.set_user(OTHER_USER)
		with self.assertRaises(frappe.ValidationError):
			self.complete(other, begin["challenge"])
		with self.assertRaises(frappe.ValidationError):
			self.complete(mine, begin["challenge"])
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.count("Employee Checkin", {"employee": ("in", [self.employee, self.other_employee])}), 0
		)
		self.assertIsNone(frappe.db.get_value("Device Checkin Key", {"key_id": other.key_id}, "last_used"))

	def test_key_deleted_after_begin_is_rejected(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id)
		frappe.set_user("Administrator")
		frappe.db.delete("Device Checkin Key", {"key_id": key.key_id})
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			self.complete(key, begin["challenge"])
		self.assertEqual(self.checkins(), 0)


class TestDeviceKeyBeacon(DeviceKeyTestCase):
	"""手机靠近签到牌收到的蓝牙码：码对就当作在场；码不对当作没带，继续按定位判断。"""

	def test_beacon_checkin_from_mobile_data(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin, record = self.begin_recording(key.key_id, ip=MOBILE_IP, beacon_rssi=-58, **self.beacon)
		self.assertEqual(set(begin), {"status", "challenge", "evidence"})
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "beacon"))
		self.assertEqual(
			(record["beacon_rssi"], record["latitude"], record["evidence"]), (-58, None, "beacon")
		)
		result = self.complete(key, begin["challenge"])
		self.assertEqual((result["status"], result["evidence"]), ("ok", "beacon"))
		self.assertEqual(
			set(result),
			{"status", "log_type", "time", "employee", "employee_name", "location", "evidence"},
		)
		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			"Employee Checkin",
			{"employee": self.employee},
			["presence_evidence", "latitude", "longitude", "checkin_method", "device_id"],
			as_dict=True,
		)
		self.assertEqual(row.presence_evidence, "beacon")
		self.assertFalse(row.latitude or row.longitude)
		self.assertEqual((row.checkin_method, row.device_id), ("Device Key", self.location))
		self.assertIn("Evidence: beacon RSSI: -58 dBm", self.audit_message())
		self.assertEqual(self.rejections(), [])

	def test_beacon_checkin_without_signal_strength(self):
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(key.key_id, ip=MOBILE_IP, **self.beacon)
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "beacon"))
		self.complete(key, begin["challenge"])
		self.assertNotIn("RSSI", self.audit_message())

	def test_wrong_beacon_falls_back_to_location(self):
		key = self.register()
		frappe.set_user(API_USER)
		wrong = self.wrong_beacon
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, beacon_rssi=-70, **wrong),
			{"status": "need_location", "reason": None},
		)
		[log] = self.rejections()
		# 日志只记时间段偏移、信号强度和机型，不记码
		self.assertEqual(log.error, "Slot offset: 0\nRSSI: -70\nDevice: Other")
		self.assertNotIn(wrong["beacon_code"], log.error)
		begin, record = self.begin_recording(
			key.key_id,
			ip=MOBILE_IP,
			latitude=NEAR[0],
			longitude=NEAR[1],
			accuracy=30,
			beacon_rssi=-70,
			**wrong,
		)
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "gps"))
		# 证明在场的不是蓝牙，信号强度就不往验证码记录里存
		self.assertIsNone(record["beacon_rssi"])
		result = self.complete(key, begin["challenge"])
		self.assertEqual(result["evidence"], "gps")
		# 退回定位后，审计里不留蓝牙的信号强度
		self.assertNotIn("RSSI", self.audit_message())
		# 每次带着错码来开始打卡，都记一条
		self.assertEqual(len(self.rejections()), 2)

	def test_rejection_log_tells_how_far_off_the_slot_was(self):
		key = self.register()
		frappe.set_user(API_USER)
		stale = BEACON_SLOT - 5
		stale_code = beacon_code(BEACON_TEST_KEY, self.location, stale)
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, beacon_slot=stale, beacon_code=stale_code)["status"],
			"need_location",
		)
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, beacon_slot=-1, beacon_code=stale_code)["status"],
			"need_location",
		)
		first, second = self.rejections()
		self.assertEqual(first.error, "Slot offset: -5\nRSSI: -\nDevice: Other")
		self.assertEqual(second.error, "Slot offset: invalid\nRSSI: -\nDevice: Other")
		self.assertNotIn(stale_code, first.error + second.error)

	def test_beacon_window_edges(self):
		key = self.register()
		for offset, expected in ((-3, "ok"), (1, "ok"), (-4, "need_location"), (2, "need_location")):
			with self.subTest(offset=offset):
				slot = BEACON_SLOT + offset
				code = beacon_code(BEACON_TEST_KEY, self.location, slot)
				frappe.set_user(API_USER)
				self.assertEqual(
					self.begin(key.key_id, ip=MOBILE_IP, beacon_slot=slot, beacon_code=code)["status"],
					expected,
				)

	def test_beacon_ignored_when_switch_off(self):
		key = self.register()
		frappe.db.set_single_value("HR Settings", "ble_checkin_enabled", 0)
		frappe.set_user(API_USER)
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, **self.beacon), {"status": "need_location", "reason": None}
		)
		self.assertEqual(
			self.begin(key.key_id, ip=MOBILE_IP, **self.wrong_beacon),
			{"status": "need_location", "reason": None},
		)
		self.assertEqual(self.rejections(), [])

	def test_beacon_ignored_for_non_pilot(self):
		# 蓝牙打卡只对开了手机钥匙打卡的人生效：不在试点名单里的人，开始打卡就先被挡住，码根本不会被核对
		self.assertTrue(ble_checkin_enabled_for(self.employee))
		self.assertFalse(ble_checkin_enabled_for(self.other_employee))
		key = self.register(user=OTHER_USER)
		frappe.set_user(OTHER_USER)
		self.assertEqual(self.begin(key.key_id, ip=MOBILE_IP, **self.beacon), {"status": "disabled"})
		self.assertEqual(self.begin(key.key_id, ip=MOBILE_IP, **self.wrong_beacon), {"status": "disabled"})
		self.assertEqual(self.rejections(), [])

	def test_beacon_ignored_when_location_has_no_key(self):
		key = self.register()
		frappe.set_user(API_USER)
		with patch.object(attendance_beacon, "_location_ble_key", return_value=None):
			self.assertFalse(ble_checkin_enabled_for(self.employee))
			self.assertEqual(
				self.begin(key.key_id, ip=MOBILE_IP, **self.wrong_beacon),
				{"status": "need_location", "reason": None},
			)
		self.assertEqual(self.rejections(), [])

	def test_half_beacon_params_are_ignored(self):
		key = self.register()
		frappe.set_user(API_USER)
		for params in (
			{"beacon_code": self.beacon["beacon_code"]},
			{"beacon_slot": BEACON_SLOT},
			{"beacon_rssi": -60},
		):
			with self.subTest(params=params):
				self.assertEqual(
					self.begin(key.key_id, ip=MOBILE_IP, **params),
					{"status": "need_location", "reason": None},
				)
		self.assertEqual(self.rejections(), [])

	def test_begin_without_beacon_is_unchanged(self):
		key = self.register()
		frappe.set_user(API_USER)
		self.assertEqual(self.begin(key.key_id, ip=MOBILE_IP), {"status": "need_location", "reason": None})
		gps = self.begin(key.key_id, ip=MOBILE_IP, latitude=NEAR[0], longitude=NEAR[1], accuracy=30)
		self.assertEqual(set(gps), {"status", "challenge", "evidence"})
		self.assertEqual((gps["status"], gps["evidence"]), ("ok", "gps"))
		self.complete(key, gps["challenge"])
		frappe.db.delete("Employee Checkin", {"employee": self.employee})
		office = self.begin(key.key_id)
		self.assertEqual(set(office), {"status", "challenge", "evidence"})
		self.assertEqual((office["status"], office["evidence"]), ("ok", "office_network"))
		self.assertEqual(self.rejections(), [])

	def test_office_network_ignores_beacon(self):
		key = self.register()
		frappe.set_user(API_USER)
		for beacon in (self.beacon, self.wrong_beacon):
			begin = self.begin(key.key_id, beacon_rssi=-50, **beacon)
			self.assertEqual((begin["status"], begin["evidence"]), ("ok", "office_network"))
			self.assertEqual(self.rejections(), [])
		result = self.complete(key, begin["challenge"])
		self.assertEqual(result["evidence"], "office_network")
		frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("Employee Checkin", {"employee": self.employee}, "presence_evidence"),
			"office_network",
		)
		self.assertNotIn("RSSI", self.audit_message())

	def test_beacon_comes_before_location(self):
		# 码对时不看定位：人在远处的定位也不会把它挡回去
		key = self.register()
		frappe.set_user(API_USER)
		begin = self.begin(
			key.key_id, ip=MOBILE_IP, latitude=35.75, longitude=139.9, accuracy=10, **self.beacon
		)
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "beacon"))

	def test_beacon_still_needs_the_device_key_and_cooldown(self):
		key = self.register()
		frappe.set_user(API_USER)
		self.assertEqual(self.begin("missing", ip=MOBILE_IP, **self.beacon), {"status": "no_device_key"})
		begin = self.begin(key.key_id, ip=MOBILE_IP, **self.beacon)
		self.complete(key, begin["challenge"])
		with self.assertRaises(frappe.ValidationError):
			self.begin(key.key_id, ip=MOBILE_IP, **self.beacon)

	def test_beacon_rejections_are_capped(self):
		key = self.register()
		frappe.set_user(API_USER)
		for _ in range(25):
			self.begin(key.key_id, ip=MOBILE_IP, **self.wrong_beacon)
		self.assertEqual(len(self.rejections()), 20)


class TestDeviceKeyWithGeolocationTracking(DeviceKeyTestCase):
	"""正式环境开着「地理位置追踪」：公司网络证明在场时，没有经纬度也能打卡。"""

	def setUp(self):
		super().setUp()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)

	def tearDown(self):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		super().tearDown()

	def test_office_network_without_location(self):
		key = self.register()
		frappe.set_user(API_USER)
		result = self.complete(key, self.begin(key.key_id)["challenge"])
		self.assertEqual((result["status"], result["evidence"]), ("ok", "office_network"))

	def test_beacon_checkin_with_geolocation_tracking_on(self):
		key = self.register()
		frappe.set_user(API_USER)
		# 开着地理位置追踪、不在公司网络、没有经纬度：蓝牙码对就能打卡
		self.assertEqual(self.begin(key.key_id, ip=MOBILE_IP), {"status": "need_location", "reason": None})
		begin = self.begin(key.key_id, ip=MOBILE_IP, beacon_rssi=-58, **self.beacon)
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "beacon"))
		result = self.complete(key, begin["challenge"])
		self.assertEqual((result["status"], result["evidence"]), ("ok", "beacon"))
		frappe.set_user("Administrator")
		row = frappe.db.get_value(
			"Employee Checkin",
			{"employee": self.employee},
			["presence_evidence", "latitude", "checkin_method"],
			as_dict=True,
		)
		self.assertEqual((row.presence_evidence, row.checkin_method), ("beacon", "Device Key"))
		self.assertFalse(row.latitude)


class TestDeviceKeyCheckinMethod(HRMSTestSuite):
	def test_audit_title(self):
		self.assertEqual(AUDIT_TITLES["Device Key"], "Device Key Checkin Audit")

	def test_attendance_day_details_recognise_device_key(self):
		self.assertEqual(mobile_attendance.punch_method("Device Key"), "device_key")
		self.assertEqual(mobile_attendance.punch_evidence("device_key", None, None), "office_network")
		self.assertEqual(mobile_attendance.punch_evidence("device_key", 35.68, 139.76), "gps")


class TestDeviceKeyList(DeviceKeyTestCase):
	def test_lists_my_keys_newest_first(self):
		old = self.register(device_name="iPhone (iPhone14,8)")
		new = self.register(device_name="iPhone (iPhone16,2)")
		self.register(user=OTHER_USER)
		frappe.db.set_value("Device Checkin Key", {"key_id": old.key_id}, "creation", "2026-10-01 09:00:00.123456")
		frappe.db.set_value("Device Checkin Key", {"key_id": old.key_id}, "last_used", "2026-10-03 08:58:12.5")
		frappe.set_user(API_USER)
		result = device_key.list_my_keys()
		self.assertEqual(result["max"], 3)
		self.assertEqual([key["key_id"] for key in result["keys"]], [new.key_id, old.key_id])
		self.assertEqual(
			result["keys"][1],
			{
				"key_id": old.key_id,
				"device_name": "iPhone (iPhone14,8)",
				"registered_at": "2026-10-01 09:00:00",
				"last_used": "2026-10-03 08:58:12",
			},
		)
		self.assertIsNone(result["keys"][0]["last_used"])

	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			device_key.list_my_keys()

	def test_delete_my_key(self):
		mine = self.register()
		other = self.register(user=OTHER_USER)
		frappe.set_user(API_USER)
		self.assertEqual(device_key.delete_my_key(key_id=other.key_id), {"status": "not_found", "key_count": 1})
		self.assertEqual(device_key.delete_my_key(key_id="missing"), {"status": "not_found", "key_count": 1})
		notifications = frappe.db.count("PWA Notification", {"to_user": API_USER})
		self.assertEqual(device_key.delete_my_key(key_id=mine.key_id), {"status": "ok", "key_count": 0})
		self.assertEqual(frappe.db.count("PWA Notification", {"to_user": API_USER}), notifications)
		frappe.set_user("Administrator")
		self.assertEqual(self.key_ids(OTHER_USER), [other.key_id])
		with self.assertRaises(frappe.ValidationError):
			frappe.set_user(API_USER)
			device_key.delete_my_key(key_id="")
