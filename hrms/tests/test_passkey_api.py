import json
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import passkey
from hrms.tests.utils import HRMSTestSuite
from hrms.tests.webauthn_soft_authenticator import SoftAuthenticator

RP_ID = "localhost"
ORIGIN = "http://localhost:29830"
API_USER = "passkey-api@example.com"
OTHER_USER = "passkey-api-other@example.com"


class PasskeyApiTestCase(HRMSTestSuite):
	rp_id = RP_ID
	origin = ORIGIN

	def setUp(self):
		frappe.set_user("Administrator")
		self.conf = patch.dict(
			frappe.local.conf, {"passkey_rp_id": self.rp_id, "passkey_origins": [self.origin]}
		)
		self.conf.start()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(API_USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for user in (API_USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
		frappe.db.delete("Passkey Credential", {"user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("PWA Notification", {"to_user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("Employee Checkin", {"employee": ("in", [self.employee, self.other_employee])})

	def tearDown(self):
		frappe.set_user("Administrator")
		self.conf.stop()

	def register_device(self, user=API_USER, authenticator=None):
		authenticator = authenticator or SoftAuthenticator(self.rp_id, self.origin, user.encode())
		frappe.set_user(user)
		options = passkey.register_options()
		response = authenticator.register(options["challenge"])
		passkey.register_complete(json.dumps(response), device_name="Test Phone")
		frappe.set_user("Administrator")
		return authenticator


class TestPasskeyRegistration(PasskeyApiTestCase):
	def test_register_stores_verified_public_key(self):
		authenticator = self.register_device()
		row = frappe.db.get_value(
			"Passkey Credential",
			{"credential_id": authenticator.credential_id_b64},
			["employee", "credential_public_key", "device_name"],
			as_dict=True,
		)
		self.assertEqual(row.employee, self.employee)
		self.assertTrue(row.credential_public_key)
		self.assertEqual(row.device_name, "Test Phone")

	def test_register_rejects_reused_or_foreign_challenge(self):
		authenticator = SoftAuthenticator(RP_ID, ORIGIN)
		frappe.set_user(OTHER_USER)
		options = passkey.register_options()
		frappe.set_user(API_USER)
		response = authenticator.register(options["challenge"])
		with self.assertRaises(frappe.ValidationError):
			passkey.register_complete(json.dumps(response))

	def test_device_limit_and_new_device_notification(self):
		self.register_device()
		self.assertFalse(frappe.db.exists("PWA Notification", {"to_user": API_USER}))
		self.register_device()
		self.assertTrue(frappe.db.exists("PWA Notification", {"to_user": API_USER}))
		self.register_device()
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			passkey.register_options()

	def test_options_exclude_existing_devices(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		options = passkey.register_options()
		self.assertEqual([c["id"] for c in options["excludeCredentials"]], [authenticator.credential_id_b64])

	def test_list_and_delete_only_own_devices(self):
		self.register_device()
		self.register_device(user=OTHER_USER)
		frappe.set_user(API_USER)
		mine = passkey.get_my_passkeys()
		self.assertEqual(len(mine), 1)
		other_name = frappe.db.get_value("Passkey Credential", {"user": OTHER_USER}, "name")
		with self.assertRaises(frappe.ValidationError):
			passkey.delete_passkey(other_name)
		passkey.delete_passkey(mine[0]["name"])
		self.assertEqual(passkey.get_my_passkeys(), [])


TEST_LOCATION = "passkey-test-door"


def ensure_location(with_geofence=True):
	if not frappe.db.exists("Shift Location", "Passkey Test Office"):
		frappe.get_doc(
			{
				"doctype": "Shift Location",
				"location_name": "Passkey Test Office",
				"latitude": 35.6812,
				"longitude": 139.7671,
				"checkin_radius": 200,
			}
		).insert()
	if not frappe.db.exists("QR Checkin Location", TEST_LOCATION):
		frappe.get_doc(
			{"doctype": "QR Checkin Location", "location_name": TEST_LOCATION, "secret": "s" * 32}
		).insert()
	frappe.db.set_value(
		"QR Checkin Location",
		TEST_LOCATION,
		"shift_location",
		"Passkey Test Office" if with_geofence else None,
	)
	return TEST_LOCATION


class TestOneTapCheckin(PasskeyApiTestCase):
	def setUp(self):
		super().setUp()
		self.location = ensure_location()
		settings = frappe.get_doc("HR Settings")
		settings.passkey_checkin_location = self.location
		settings.passkey_checkin_enabled_for_all = 0
		settings.set("passkey_checkin_pilot_employees", [{"employee": self.employee}])
		settings.qr_checkin_allowed_ips = "203.0.113.0/24"
		settings.save()

	def _begin(self, ip="198.51.100.1", **kwargs):
		with patch.object(passkey, "get_client_ip", return_value=ip):
			return passkey.begin_checkin("IN", **kwargs)

	def _complete(self, authenticator, options, **kwargs):
		assertion = authenticator.authenticate(options["challenge"], **kwargs)
		with patch("frappe.publish_realtime"):
			return passkey.complete_checkin(json.dumps(assertion))

	def test_context_for_pilot_and_non_pilot(self):
		self.register_device()
		frappe.set_user(API_USER)
		with patch.object(passkey, "get_client_ip", return_value="203.0.113.5"):
			context = passkey.get_checkin_context()
		self.assertEqual(
			(context["enabled"], context["has_passkey"], context["on_office_network"]), (True, True, True)
		)
		self.assertEqual(context["location"]["name"], self.location)
		frappe.set_user(OTHER_USER)
		self.assertFalse(passkey.get_checkin_context()["enabled"])

	def test_office_network_one_tap_checkin(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		begin = self._begin(ip="203.0.113.5")
		self.assertEqual((begin["status"], begin["evidence"]), ("ok", "office_network"))
		result = self._complete(authenticator, begin["options"])
		frappe.set_user("Administrator")
		self.assertEqual(result["log_type"], "IN")
		self.assertEqual(
			frappe.db.get_value("Employee Checkin", {"employee": self.employee}, "checkin_method"), "Passkey"
		)

	def test_mobile_data_needs_location_then_uses_gps(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		self.assertEqual(self._begin()["status"], "need_location")
		begin = self._begin(latitude=35.6813, longitude=139.7672, accuracy=30)
		self.assertEqual(begin["evidence"], "gps")
		self._complete(authenticator, begin["options"])
		frappe.set_user("Administrator")
		row = frappe.db.get_value("Employee Checkin", {"employee": self.employee}, ["latitude"], as_dict=True)
		self.assertAlmostEqual(row.latitude, 35.6813, places=4)

	def test_forged_signature_is_rejected(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		begin = self._begin(ip="203.0.113.5")
		with self.assertRaisesRegex(frappe.ValidationError, "could not be verified"):
			self._complete(authenticator, begin["options"], tamper_signature=True)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee}))

	def test_far_away_is_presence_unconfirmed(self):
		self.register_device()
		frappe.set_user(API_USER)
		begin = self._begin(latitude=35.75, longitude=139.9, accuracy=10)
		self.assertEqual((begin["status"], begin["reason"]), ("presence_unconfirmed", "too_far"))

	def test_disabled_for_non_pilot_and_no_passkey_status(self):
		frappe.set_user(OTHER_USER)
		self.assertEqual(self._begin(ip="203.0.113.5")["status"], "disabled")
		frappe.set_user(API_USER)
		self.assertEqual(self._begin(ip="203.0.113.5")["status"], "no_passkey")

	def test_complete_checkin_rejects_credential_of_another_user(self):
		self.register_device()
		other = self.register_device(user=OTHER_USER)
		frappe.set_user(API_USER)
		begin = self._begin(ip="203.0.113.5")
		before = frappe.db.get_value("Passkey Credential", {"user": OTHER_USER}, "last_used")
		with self.assertRaises(frappe.ValidationError):
			self._complete(other, begin["options"])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Passkey Credential", {"user": OTHER_USER}, "last_used"), before)
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee}))

	def test_challenge_cannot_be_replayed(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		begin = self._begin(ip="203.0.113.5")
		assertion = authenticator.authenticate(begin["options"]["challenge"])
		with patch("frappe.publish_realtime"):
			passkey.complete_checkin(json.dumps(assertion))
			with self.assertRaises(frappe.ValidationError):
				passkey.complete_checkin(json.dumps(assertion))

	def test_cooldown_blocks_before_face_id(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		self._complete(authenticator, self._begin(ip="203.0.113.5")["options"])
		with self.assertRaises(frappe.ValidationError):
			self._begin(ip="203.0.113.5")

	def test_invalid_log_type(self):
		frappe.set_user(API_USER)
		with patch.object(passkey, "get_client_ip", return_value="203.0.113.5"):
			with self.assertRaises(frappe.ValidationError):
				passkey.begin_checkin("SIDEWAYS")


class TestCheckinWithGeolocationTracking(PasskeyApiTestCase):
	"""正式环境开着「地理位置追踪」：Employee Checkin 自身要求有经纬度。"""

	def setUp(self):
		super().setUp()
		self.location = ensure_location()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)
		settings = frappe.get_doc("HR Settings")
		settings.passkey_checkin_location = self.location
		settings.passkey_checkin_enabled_for_all = 0
		settings.set("passkey_checkin_pilot_employees", [{"employee": self.employee}])
		settings.qr_checkin_allowed_ips = "203.0.113.0/24"
		settings.save()

	def tearDown(self):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		super().tearDown()

	def _one_tap(self, authenticator, ip, **position):
		frappe.set_user(API_USER)
		with patch.object(passkey, "get_client_ip", return_value=ip):
			begin = passkey.begin_checkin("IN", **position)
		assertion = authenticator.authenticate(begin["options"]["challenge"])
		with patch("frappe.publish_realtime"):
			result = passkey.complete_checkin(json.dumps(assertion))
		frappe.set_user("Administrator")
		return begin, result

	def test_office_network_one_tap_without_location(self):
		authenticator = self.register_device()
		begin, result = self._one_tap(authenticator, "203.0.113.5")
		self.assertEqual((begin["evidence"], result["status"]), ("office_network", "ok"))

	def test_gps_one_tap(self):
		authenticator = self.register_device()
		begin, result = self._one_tap(
			authenticator, "198.51.100.1", latitude=35.6813, longitude=139.7672, accuracy=20
		)
		self.assertEqual((begin["evidence"], result["status"]), ("gps", "ok"))

	def test_untrusted_checkin_still_needs_coordinates(self):
		doc = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"log_type": "IN",
				"time": frappe.utils.now(),
			}
		)
		doc.flags.presence_evidence = "office_network"
		with self.assertRaises(frappe.ValidationError):
			doc.insert()
