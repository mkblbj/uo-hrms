"""App 推送：设备登记 / 注销（S3）、四类开关（S4）、APNs 发送（S5）。HTTP 用替身，不连苹果。"""

import json
import os
import tempfile
import time
import uuid
from unittest.mock import MagicMock, patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

import frappe

from hrms.api import mobile
from hrms.tests.test_mobile_api import ensure_user
from hrms.tests.utils import HRMSTestSuite
from hrms.utils import apns

USER = "mobile-push@example.com"
OTHER_USER = "mobile-push-other@example.com"
DEVICE = "Mobile App Device"
TEAM_ID = "TEAMID1234"


def token(seed: int) -> str:
	return f"{seed:064x}"


class FakeResponse:
	def __init__(self, status: int, body: dict | None = None):
		self.status_code = status
		self.content = json.dumps(body).encode() if body else b""

	def json(self):
		return json.loads(self.content)


class FakeAPNs:
	"""假的 httpx.Client：记下每个请求，按顺序回应（默认 200）。"""

	def __init__(self, *responses):
		self.responses = list(responses)
		self.requests = []
		self.client_kwargs = None

	def client(self, **kwargs):
		self.client_kwargs = kwargs
		return self

	def __enter__(self):
		return self

	def __exit__(self, *args):
		return False

	def post(self, url, headers=None, content=None):
		self.requests.append({"url": url, "headers": headers, "payload": json.loads(content)})
		status, body = self.responses.pop(0) if self.responses else (200, None)
		return FakeResponse(status, body)


class FakeQueue:
	"""假的 RQ 队列：记下入队的方法和参数。"""

	count = 0

	def __init__(self):
		self.jobs = []

	def enqueue_call(self, *args, **kwargs):
		queued = kwargs["kwargs"]
		self.jobs.append({"method": queued["method"], **queued["kwargs"]})


class PushTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		for user in (USER, OTHER_USER):
			ensure_user(user)
			frappe.db.set_value("User", user, "enabled", 1)
		frappe.db.delete(DEVICE, {"user": ["in", [USER, OTHER_USER]]})
		frappe.db.delete("Mobile Push Settings", {"user": ["in", [USER, OTHER_USER]]})
		frappe.db.delete("PWA Notification", {"to_user": ["in", [USER, OTHER_USER]]})

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def register(self, user=USER, seed=1, installation=None, **overrides):
		frappe.set_user(user)
		values = {
			"device_token": token(seed),
			"environment": "sandbox",
			"bundle_id": "com.toiroworld.hrms.dev",
			"installation_id": installation or str(uuid.uuid4()),
			"app_version": "1.0 (14)",
			"os_version": "26.1",
			"device_model": "iPhone16,2",
			**overrides,
		}
		result = mobile.register_push_device(**values)
		frappe.set_user("Administrator")
		return result


class TestPushDevices(PushTestCase):
	def test_register_creates_device(self):
		installation = str(uuid.uuid4())
		self.assertEqual(self.register(installation=installation), {"status": "ok"})
		row = frappe.db.get_value(DEVICE, {"device_token": token(1)}, ["*"], as_dict=True)
		self.assertEqual(row.user, USER)
		self.assertEqual(
			(row.environment, row.bundle_id, row.installation_id), ("sandbox", "com.toiroworld.hrms.dev", installation)
		)
		self.assertEqual((row.app_version, row.os_version, row.device_model), ("1.0 (14)", "26.1", "iPhone16,2"))
		self.assertIsNotNone(row.last_seen)

	def test_uppercase_token_is_stored_lowercase(self):
		self.register(device_token=token(0xABC).upper())
		self.assertTrue(frappe.db.exists(DEVICE, {"device_token": token(0xABC)}))

	def test_invalid_values_are_417(self):
		cases = {
			"short token": {"device_token": "ab" * 31},
			"not hex": {"device_token": "g" * 64},
			"long token": {"device_token": "a" * 202},
			"environment": {"environment": "development"},
			"bundle": {"bundle_id": "com.example.app"},
			"installation": {"installation_id": "not-a-uuid"},
			"missing token": {"device_token": None},
		}
		for label, override in cases.items():
			with self.subTest(label), self.assertRaises(frappe.ValidationError):
				self.register(**override)
		self.assertFalse(frappe.db.exists(DEVICE, {"user": USER}))

	def test_guest_cannot_register(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			mobile.register_push_device(token(1), "sandbox", "com.toiroworld.hrms.dev", str(uuid.uuid4()))

	def test_same_token_moves_to_the_new_account(self):
		installation = str(uuid.uuid4())
		self.register(installation=installation)
		self.register(user=OTHER_USER, installation=installation, environment="production")
		rows = frappe.get_all(DEVICE, filters={"device_token": token(1)}, fields=["user", "environment"])
		self.assertEqual(rows, [{"user": OTHER_USER, "environment": "production"}])

	def test_new_token_for_same_installation_replaces_old(self):
		installation = str(uuid.uuid4())
		self.register(seed=1, installation=installation)
		self.register(seed=2, installation=installation)
		self.assertEqual(frappe.get_all(DEVICE, filters={"user": USER}, pluck="device_token"), [token(2)])

	def test_keeps_the_ten_most_recent_devices(self):
		for seed in range(1, 12):
			self.register(seed=seed)
			frappe.db.set_value(DEVICE, {"device_token": token(seed)}, "last_seen", f"2026-10-{seed:02d} 09:00:00")
		self.register(seed=12)
		tokens = set(frappe.get_all(DEVICE, filters={"user": USER}, pluck="device_token"))
		self.assertEqual(len(tokens), 10)
		self.assertNotIn(token(1), tokens)
		self.assertNotIn(token(2), tokens)
		self.assertIn(token(12), tokens)

	def test_unregister_only_removes_own_device(self):
		self.register(seed=1)
		self.register(user=OTHER_USER, seed=2)
		frappe.set_user(USER)
		self.assertEqual(mobile.unregister_push_device(token(2)), {"status": "ok"})
		self.assertEqual(mobile.unregister_push_device(token(99)), {"status": "ok"})
		self.assertEqual(mobile.unregister_push_device(token(1)), {"status": "ok"})
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists(DEVICE, {"device_token": token(1)}))
		self.assertTrue(frappe.db.exists(DEVICE, {"device_token": token(2)}))


class TestPushSettings(PushTestCase):
	def test_defaults_are_all_on(self):
		frappe.set_user(USER)
		self.assertEqual(
			mobile.get_push_settings(),
			{"api_version": 1, "shift_reminder": True, "shift_change": True, "approval": True, "announcement": True},
		)

	def test_partial_updates_keep_the_rest(self):
		frappe.set_user(USER)
		result = mobile.update_push_settings(cmd="hrms.api.mobile.update_push_settings", shift_reminder=False)
		self.assertEqual(
			result,
			{"api_version": 1, "shift_reminder": False, "shift_change": True, "approval": True, "announcement": True},
		)
		result = mobile.update_push_settings(approval=False)
		self.assertFalse(result["shift_reminder"])
		self.assertFalse(result["approval"])
		self.assertEqual(mobile.get_push_settings(), result)
		frappe.set_user(OTHER_USER)
		self.assertTrue(mobile.get_push_settings()["shift_reminder"])

	def test_unknown_keys_or_non_booleans_are_417(self):
		frappe.set_user(USER)
		for settings in ({"other": False}, {"shift_reminder": "false"}, {"approval": 0}, {"announcement": None}):
			with self.subTest(settings), self.assertRaises(frappe.ValidationError):
				mobile.update_push_settings(**settings)
		self.assertTrue(all(mobile.get_push_settings()[key] for key in ("shift_reminder", "approval", "announcement")))


class APNsTestCase(PushTestCase):
	def setUp(self):
		super().setUp()
		self.private_key = ec.generate_private_key(ec.SECP256R1())
		key_file = tempfile.NamedTemporaryFile("wb", suffix=".p8", delete=False)
		key_file.write(
			self.private_key.private_bytes(
				serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
			)
		)
		key_file.close()
		self.addCleanup(os.unlink, key_file.name)
		self.key_id = f"K{uuid.uuid4().hex[:9].upper()}"
		self.config = {"team_id": TEAM_ID, "key_id": self.key_id, "key_path": key_file.name}
		conf = patch.dict(frappe.local.conf, {"uohr_apns": self.config})
		conf.start()
		self.addCleanup(conf.stop)
		self.queue = FakeQueue()
		queue = patch("frappe.utils.background_jobs.get_queue", return_value=self.queue)
		queue.start()
		self.addCleanup(queue.stop)
		web_push = patch("frappe.push_notification.PushNotification")
		self.web_push = web_push.start().return_value
		self.web_push.is_enabled.return_value = True
		self.addCleanup(web_push.stop)

	def notify(self, user=USER, defer=True, **values):
		doc = frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"from_user": "Administrator",
				"to_user": user,
				"notification_title": "明日の勤務予定",
				"notification_type": "Shift Reminder",
				"reference_date": "2026-10-21",
				"message": "明日（10月21日）は9:00〜18:00の勤務です。ご確認をお願いいたします。",
				**values,
			}
		)
		doc.flags.defer_push_notification = defer
		return doc.insert(ignore_permissions=True)

	def send(self, notification, *responses):
		fake = FakeAPNs(*responses)
		with patch("httpx.Client", side_effect=fake.client):
			apns.send_notification(str(notification.name))
		return fake


class TestAPNsPayload(APNsTestCase):
	def test_shift_reminder_payload(self):
		doc = self.notify()
		payload = apns.payload_for(str(doc.name))
		self.assertEqual(
			payload,
			{
				"aps": {
					"alert": {
						"title": "明日の勤務予定",
						"body": "明日（10月21日）は9:00〜18:00の勤務です。ご確認をお願いいたします。",
					},
					"sound": "default",
					"badge": 1,
					"thread-id": "shift_reminder",
				},
				"uohr": {
					"v": 1,
					"notification": str(doc.name),
					"type": "shift_reminder",
					"target": {"screen": "roster", "date": "2026-10-21"},
				},
			},
		)

	def test_default_titles_by_type(self):
		expected = {
			"Shift Reminder": "明日のシフト",
			"Shift Change": "シフトの変更",
			"Approval": "申請・承認",
			"Announcement": "会社からのお知らせ",
			"Other": "お知らせ",
		}
		for notification_type, title in expected.items():
			doc = self.notify(notification_title=None, notification_type=notification_type)
			with self.subTest(notification_type):
				payload = apns.payload_for(str(doc.name))
				self.assertEqual(payload["aps"]["alert"]["title"], title)
				self.assertEqual(payload["aps"]["thread-id"], payload["uohr"]["type"])

	def test_body_is_plain_text_and_truncated(self):
		doc = self.notify(
			notification_type="Announcement",
			message="<p>健康診断&amp;説明会</p><p>場所は<b>本社</b>&nbsp;3階</p>",
		)
		self.assertEqual(apns.payload_for(str(doc.name))["aps"]["alert"]["body"], "健康診断&説明会 場所は本社 3階")
		doc = self.notify(notification_type="Announcement", use_html_source=1, html_source="<div>" + "あ" * 300 + "</div>")
		body = apns.payload_for(str(doc.name))["aps"]["alert"]["body"]
		self.assertEqual(len(body), 178)
		self.assertTrue(body.endswith("…"))

	def test_badge_counts_unread_notifications(self):
		self.notify()
		read = self.notify()
		frappe.db.set_value("PWA Notification", read.name, "read", 1)
		doc = self.notify()
		self.assertEqual(apns.payload_for(str(doc.name))["aps"]["badge"], 2)

	def test_payload_has_no_user_details(self):
		doc = self.notify()
		text = json.dumps(apns.payload_for(str(doc.name)))
		self.assertNotIn(USER, text)
		self.assertNotIn("Administrator", text)


class TestAPNsSending(APNsTestCase):
	def test_sends_to_every_device_with_headers(self):
		self.register(seed=1)
		self.register(seed=2, environment="production", bundle_id="com.toiroworld.hrms")
		doc = self.notify()
		before = int(time.time())
		fake = self.send(doc)

		self.assertTrue(fake.client_kwargs["http2"])
		urls = sorted(request["url"] for request in fake.requests)
		self.assertEqual(
			urls,
			[
				f"https://api.push.apple.com/3/device/{token(2)}",
				f"https://api.sandbox.push.apple.com/3/device/{token(1)}",
			],
		)
		for request in fake.requests:
			headers = request["headers"]
			self.assertEqual(headers["apns-push-type"], "alert")
			self.assertEqual(headers["apns-priority"], "10")
			self.assertEqual(headers["apns-collapse-id"], str(doc.name))
			self.assertAlmostEqual(int(headers["apns-expiration"]), before + 24 * 3600, delta=5)
			self.assertEqual(request["payload"]["uohr"]["notification"], str(doc.name))
			provider_token = headers["authorization"].removeprefix("bearer ")
			self.assertEqual(jwt.get_unverified_header(provider_token), {"alg": "ES256", "kid": self.key_id})
			claims = jwt.decode(provider_token, self.private_key.public_key(), algorithms=["ES256"])
			self.assertEqual(claims["iss"], TEAM_ID)
			self.assertAlmostEqual(claims["iat"], before, delta=5)
		topics = {request["url"].split("/")[-1]: request["headers"]["apns-topic"] for request in fake.requests}
		self.assertEqual(topics, {token(1): "com.toiroworld.hrms.dev", token(2): "com.toiroworld.hrms"})

	def test_provider_token_is_reused(self):
		self.register()
		first = self.send(self.notify())
		second = self.send(self.notify())
		self.assertEqual(
			first.requests[0]["headers"]["authorization"], second.requests[0]["headers"]["authorization"]
		)

	def test_switched_off_type_is_not_sent_but_other_always_is(self):
		self.register()
		frappe.set_user(USER)
		mobile.update_push_settings(shift_reminder=False, shift_change=False, approval=False, announcement=False)
		frappe.set_user("Administrator")
		self.assertEqual(self.send(self.notify()).requests, [])
		other = self.send(self.notify(notification_title="顔認証打刻の端末が登録されました", notification_type="Other"))
		self.assertEqual(len(other.requests), 1)

	def test_disabled_user_gets_nothing(self):
		self.register()
		doc = self.notify()
		frappe.db.set_value("User", USER, "enabled", 0)
		self.assertEqual(self.send(doc).requests, [])

	def test_without_config_nothing_happens(self):
		self.register()
		with patch.dict(frappe.local.conf, {"uohr_apns": None}):
			doc = self.notify(defer=False)
			frappe.db.after_commit.run()
			self.assertEqual(self.send(doc).requests, [])
		self.assertEqual(self.queue.jobs, [])
		# 网页推送照旧
		self.web_push.send_notification_to_user.assert_called_once()

	def test_gone_or_bad_tokens_remove_the_device(self):
		for status, reason in ((410, "Unregistered"), (400, "BadDeviceToken"), (400, "DeviceTokenNotForTopic")):
			with self.subTest(reason):
				self.register(seed=7)
				self.send(self.notify(), (status, {"reason": reason}))
				self.assertFalse(frappe.db.exists(DEVICE, {"device_token": token(7)}))

	def test_other_rejections_are_logged_and_device_kept(self):
		self.register()
		with patch.object(frappe, "log_error") as log_error:
			self.send(self.notify(), (400, {"reason": "PayloadTooLarge"}))
		self.assertTrue(frappe.db.exists(DEVICE, {"device_token": token(1)}))
		self.assertEqual(log_error.call_count, 1)
		self.assertNotIn(token(1), str(log_error.call_args))

	def test_expired_provider_token_is_logged_and_dropped(self):
		self.register()
		first = self.send(self.notify())
		with patch.object(frappe, "log_error") as log_error:
			self.send(self.notify(), (403, {"reason": "ExpiredProviderToken"}))
		log_error.assert_called_once()
		self.assertIn("ExpiredProviderToken", str(log_error.call_args))
		with patch("time.time", return_value=time.time() + 5):
			third = self.send(self.notify())
		self.assertNotEqual(
			first.requests[0]["headers"]["authorization"], third.requests[0]["headers"]["authorization"]
		)

	def test_unreadable_key_is_logged_once_per_send(self):
		self.register()
		with (
			patch.dict(frappe.local.conf, {"uohr_apns": {**self.config, "key_path": "/nonexistent.p8"}}),
			patch.object(frappe, "log_error") as log_error,
		):
			fake = self.send(self.notify())
		self.assertEqual(fake.requests, [])
		log_error.assert_called_once()

	def test_busy_or_down_retries_once_after_a_minute(self):
		self.register(seed=1)
		self.register(seed=2)
		doc = self.notify()
		self.send(doc, (200, None), (429, {"reason": "TooManyRequests"}))
		[job] = self.queue.jobs
		self.assertEqual(job["method"], "hrms.utils.apns.retry_notification")
		self.assertEqual(job["notification"], str(doc.name))
		self.assertEqual(len(job["devices"]), 1)
		self.assertAlmostEqual(job["not_before"], time.time() + 60, delta=5)

		fake = FakeAPNs((503, None))
		with (
			patch("httpx.Client", side_effect=fake.client),
			patch("time.sleep") as sleep,
			patch.object(frappe, "log_error") as log_error,
		):
			apns.retry_notification(job["notification"], job["devices"], job["not_before"])
		self.assertGreater(sleep.call_args.args[0], 50)
		self.assertEqual(len(fake.requests), 1)
		self.assertEqual(len(self.queue.jobs), 1)
		log_error.assert_called_once()


	def test_retry_skips_a_device_that_changed_account(self):
		self.register(seed=1)
		doc = self.notify()
		self.send(doc, (503, None))
		[job] = self.queue.jobs
		frappe.db.set_value(DEVICE, job["devices"][0], "user", OTHER_USER)
		fake = FakeAPNs()
		with patch("httpx.Client", side_effect=fake.client), patch("time.sleep"):
			apns.retry_notification(job["notification"], job["devices"], job["not_before"])
		self.assertEqual(fake.requests, [])


class TestQueueing(APNsTestCase):
	def test_queued_after_commit_and_dropped_on_rollback(self):
		self.register()
		self.notify(defer=False)
		self.assertEqual(self.queue.jobs, [])
		frappe.db.rollback()
		frappe.db.after_commit.run()
		self.assertEqual(self.queue.jobs, [])

	def test_immediate_notification_queues_on_commit(self):
		self.register()
		doc = self.notify(defer=False)
		frappe.db.after_commit.run()
		self.assertEqual(self.queue.jobs, [{"method": "hrms.utils.apns.send_notification", "notification": str(doc.name)}])
		self.web_push.send_notification_to_user.assert_called_once()

	def test_deferred_notification_queues_from_after_commit(self):
		self.register()
		doc = self.notify()
		frappe.db.after_commit.add(doc.send_push_notification)
		self.assertEqual(self.queue.jobs, [])
		frappe.db.after_commit.run()
		self.assertEqual(self.queue.jobs, [{"method": "hrms.utils.apns.send_notification", "notification": str(doc.name)}])
		self.web_push.send_notification_to_user.assert_called_once()

	def test_no_device_no_job(self):
		self.notify(defer=False)
		frappe.db.after_commit.run()
		self.assertEqual(self.queue.jobs, [])

	def test_queue_failure_does_not_break_the_notification(self):
		self.register()
		with (
			patch("hrms.utils.apns.queue_push", side_effect=RuntimeError("redis down")),
			patch.object(frappe, "log_error"),
		):
			doc = self.notify(defer=False)
		self.assertTrue(frappe.db.exists("PWA Notification", doc.name))
		self.web_push.send_notification_to_user.assert_called_once()
