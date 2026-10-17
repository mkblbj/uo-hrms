"""Real database contract tests for the read-only sign (test site only)."""

import io
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

import frappe
from frappe.utils.response import build_response

from hrms.api import attendance_sign


class TestAttendanceSign(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.location = "sign-test-" + frappe.generate_hash(length=8)
		self.doc = frappe.get_doc(
			{
				"doctype": "QR Checkin Location",
				"location_name": self.location,
				"secret": "s" * 32,
				"enabled": 1,
				"require_display_key": 0,
			}
		).insert()
		self.key = self.doc.get_password("display_key")
		self.request_before = getattr(frappe.local, "request", None)
		self._headers(self.key)
		self.clock = datetime(2026, 10, 15, 9, 2, tzinfo=ZoneInfo("Asia/Tokyo"))
		self.now_patch = patch.object(attendance_sign.time, "time", return_value=self.clock.timestamp())
		self.tz_patch = patch.object(attendance_sign, "get_system_timezone", return_value="Asia/Tokyo")
		self.now_patch.start()
		self.tz_patch.start()
		frappe.local.response = frappe._dict()
		frappe.local.response_headers.clear()

	def tearDown(self):
		self.now_patch.stop()
		self.tz_patch.stop()
		frappe.db.rollback()
		frappe.local.request = self.request_before
		frappe.set_user("Administrator")

	def _headers(self, key):
		headers = {"X-Attendance-Sign-Key": key} if key else {}
		frappe.local.request = Request(EnvironBuilder(headers=headers).get_environ())

	def _row(self, name, *, age=1, log_type="IN", method="QR", location=None):
		created = self.clock.replace(tzinfo=None) - timedelta(seconds=age)
		frappe.db.sql(
			"""INSERT INTO `tabEmployee Checkin`
			(name, creation, modified, owner, modified_by, docstatus, idx,
			employee, employee_name, log_type, time, device_id, checkin_method)
			VALUES (%s,%s,%s,'Administrator','Administrator',0,0,%s,%s,%s,%s,%s,%s)""",
			(
				name,
				created,
				created,
				"HR-EMP-sign-example",
				"山田太郎",
				log_type,
				created,
				location or self.location,
				method,
			),
		)

	def test_requires_actual_key_even_when_web_key_is_optional(self):
		frappe.set_user("Guest")
		for key in (None, "wrong"):
			with self.subTest(key=key):
				self._headers(key)
				with self.assertRaises(frappe.PermissionError):
					attendance_sign.get_events(self.location)
		self._headers(self.key)
		self.assertEqual(attendance_sign.get_events(self.location)["events"], [])

	def test_rejects_disabled_or_other_location(self):
		with self.assertRaises(frappe.PermissionError):
			attendance_sign.get_events("another-door")
		frappe.db.set_value("QR Checkin Location", self.location, "enabled", 0)
		with self.assertRaises(frappe.PermissionError):
			attendance_sign.get_events(self.location)

	def test_qr_requires_actual_key_even_when_web_key_is_optional(self):
		frappe.set_user("Guest")
		for key in (None, "wrong"):
			self._headers(key)
			with self.assertRaises(frappe.PermissionError):
				attendance_sign.get_qr(self.location)
		self._headers(self.key)
		frappe.db.set_value("QR Checkin Location", self.location, "qr_refresh_interval", 120)
		before = frappe.db.count("Employee Checkin")
		result = attendance_sign.get_qr(self.location)
		self.assertEqual((result["version"], result["locale"], result["expires_in"]), (1, "ja-JP", 120))
		self.assertEqual(result["location"], self.location)
		self.assertEqual(result["server_time"], int(self.clock.timestamp()))
		self.assertTrue(0 < result["refresh_at"] - result["server_time"] <= 120)
		self.assertEqual(result["expires_at"] - result["refresh_at"], 120)
		self.assertEqual(frappe.db.count("Employee Checkin"), before)
		self.assertNotIn("secret", result)
		self.assertNotIn("display_key", result)
		frappe.local.response["message"] = result
		from frappe.app import process_response

		response = build_response("json")
		process_response(response)
		self.assertIn("no-store", response.headers["Cache-Control"])

	def test_qr_rejects_cross_location_key_and_disabled_location(self):
		other = frappe.get_doc(
			{
				"doctype": "QR Checkin Location",
				"location_name": "other-" + frappe.generate_hash(length=8),
				"secret": "x" * 32,
				"enabled": 1,
			}
		).insert()
		with self.assertRaises(frappe.PermissionError):
			attendance_sign.get_qr(other.name)
		frappe.db.set_value("QR Checkin Location", self.location, "enabled", 0)
		with self.assertRaises(frappe.PermissionError):
			attendance_sign.get_qr(self.location)

	def test_events_are_recent_committed_checkin_shape(self):
		self._row("sign-example")
		result = attendance_sign.get_events(self.location)
		self.assertEqual((result["version"], result["locale"]), (1, "ja-JP"))
		self.assertEqual(result["server_time"], self.clock.timestamp())
		self.assertEqual(
			result["events"],
			[
				{
					"id": "sign-example",
					"employee_id": "HR-EMP-sign-example",
					"employee_name": "山田太郎",
					"log_type": "IN",
					"time_label": "09:01",
					"created_at": self.clock.timestamp() - 1,
					"action_label": "出勤完了",
					"greeting": "おはようございます。",
					"audio_url": None,
				}
			],
		)

	def test_filters_and_orders_burst(self):
		self._row("sign-z", age=3)
		self._row("sign-b", age=2, method="Passkey", log_type="OUT")
		self._row("sign-a", age=2)
		self._row("sign-stale", age=31)
		self._row("sign-future", age=-1)
		self._row("sign-correction", method="Attendance Correction")
		self._row("sign-other", location="another-door")
		self._row("sign-invalid", log_type="")
		result = attendance_sign.get_events(self.location)
		self.assertEqual([x["id"] for x in result["events"]], ["sign-z", "sign-a", "sign-b"])
		self.assertEqual(result["events"][-1]["action_label"], "退勤完了")

	def test_returns_twenty_most_recent_events(self):
		for i in range(25):
			self._row(f"sign-limit-{i:02d}", age=25 - i)
		self.assertEqual(
			[x["id"] for x in attendance_sign.get_events(self.location)["events"]],
			[f"sign-limit-{i:02d}" for i in range(5, 25)],
		)

	def test_response_is_not_cached(self):
		frappe.local.response["message"] = attendance_sign.get_events(self.location)
		from frappe.app import process_response

		response = build_response("json")
		process_response(response)
		self.assertIn("no-store", response.headers["Cache-Control"])

	def _bundle(self, rate=24000):
		import hashlib
		import json
		import wave

		from hrms.utils import attendance_sign_audio as audio

		self.audio_temp = tempfile.TemporaryDirectory()
		self.addCleanup(self.audio_temp.cleanup)
		self.source = Path(self.audio_temp.name) / "source"
		(self.source / "audio").mkdir(parents=True)
		self.store = Path(self.audio_temp.name) / "store"
		root_patch = patch.object(audio, "_store_path", return_value=self.store)
		root_patch.start()
		self.addCleanup(root_patch.stop)
		buffer = io.BytesIO()
		with wave.open(buffer, "wb") as stream:
			stream.setnchannels(1)
			stream.setsampwidth(2)
			stream.setframerate(rate)
			stream.writeframes(b"\0\0" * rate)
		self.wav = buffer.getvalue()
		self.asset_id = hashlib.sha256(self.wav).hexdigest()
		(self.source / "audio" / (self.asset_id + ".wav")).write_bytes(self.wav)
		self.manifest = {
			"version": 1,
			"locale": "ja-JP",
			"clips": {
				"HR-EMP-sign-example": {
					kind: {"employee_name": "山田太郎", "asset_id": self.asset_id} for kind in ("IN", "OUT")
				}
			},
		}
		(self.source / "manifest.json").write_text(json.dumps(self.manifest))
		return audio

	def test_import_validates_wav_and_hash(self):
		audio = self._bundle()
		self.assertEqual(audio.install_bundle(str(self.source))["clips"], 2)
		self.assertEqual((self.store / "audio" / (self.asset_id + ".wav")).read_bytes(), self.wav)
		(self.source / "audio" / (self.asset_id + ".wav")).write_bytes(b"bad")
		with self.assertRaises(ValueError):
			audio.install_bundle(str(self.source))

	def test_missing_or_renamed_clip_is_null(self):
		audio = self._bundle()
		self.assertIsNone(audio.find_clip("HR-EMP-sign-example", "山田太郎", "IN"))
		audio.install_bundle(str(self.source))
		self.assertEqual(audio.find_clip("HR-EMP-sign-example", "山田太郎", "IN"), self.asset_id)
		self.assertIsNone(audio.find_clip("HR-EMP-sign-example", "佐藤太郎", "IN"))
		self._row("sign-with-audio")
		url = attendance_sign.get_events(self.location)["events"][0]["audio_url"]
		self.assertIn(self.asset_id, url)

	def test_audio_requires_key_and_manifest_membership(self):
		audio = self._bundle()
		audio.install_bundle(str(self.source))
		self._headers("wrong")
		with self.assertRaises(frappe.PermissionError):
			attendance_sign.get_audio(self.location, self.asset_id)
		self._headers(self.key)
		with self.assertRaises(frappe.DoesNotExistError):
			attendance_sign.get_audio(self.location, "0" * 64)

	def test_audio_response_is_wav_bytes(self):
		audio = self._bundle()
		audio.install_bundle(str(self.source))
		attendance_sign.get_audio(self.location, self.asset_id)
		response = build_response()
		self.assertEqual(response.mimetype, "audio/wav")
		self.assertEqual(response.data, self.wav)

	def test_legacy_published_16khz_remains_downloadable_during_firmware_upgrade(self):
		audio = self._bundle(rate=16000)
		audio.write_bundle(self.store, self.manifest, {self.asset_id: self.wav})
		attendance_sign.get_audio(self.location, self.asset_id)
		self.assertEqual(build_response().data, self.wav)

	def test_rejects_asset_paths(self):
		audio = self._bundle()
		audio.install_bundle(str(self.source))
		for path in ("../../site_config.json", "/etc/passwd", "../" + self.asset_id):
			with self.subTest(path=path), self.assertRaises(frappe.DoesNotExistError):
				attendance_sign.get_audio(self.location, path)

	def test_invalid_bundle_keeps_previous_manifest(self):
		audio = self._bundle()
		audio.install_bundle(str(self.source))
		before = (self.store / "manifest.json").read_bytes()
		(self.source / "audio" / (self.asset_id + ".wav")).write_bytes(b"broken")
		with self.assertRaises(ValueError):
			audio.install_bundle(str(self.source))
		self.assertEqual((self.store / "manifest.json").read_bytes(), before)

	def test_bundle_install_requires_system_manager(self):
		audio = self._bundle()
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			audio.install_bundle(str(self.source))

	def test_commit_and_rollback_visible_to_independent_http_requests(self):
		import json
		import threading
		from urllib.request import Request as URLRequest
		from urllib.request import urlopen

		from werkzeug.serving import make_server

		from frappe.app import application

		audio = self._bundle()
		audio.install_bundle(str(self.source))
		server = make_server("127.0.0.1", 0, application, threaded=True)
		thread = threading.Thread(target=server.serve_forever, daemon=True)
		thread.start()
		try:
			frappe.db.commit()
			self._row("sign-http-committed")
			frappe.db.commit()
			self._row("sign-http-rolled-back")
			frappe.db.rollback()
			request = URLRequest(
				f"http://127.0.0.1:{server.server_port}/api/method/hrms.api.attendance_sign.get_events?location={self.location}",
				headers={"X-Attendance-Sign-Key": self.key, "X-Frappe-Site-Name": frappe.local.site},
			)
			with urlopen(request, timeout=10) as response:
				data = json.load(response)
				self.assertIn("no-store", response.headers["Cache-Control"])
			self.assertEqual([x["id"] for x in data["message"]["events"]], ["sign-http-committed"])
			audio_request = URLRequest(
				f"http://127.0.0.1:{server.server_port}" + data["message"]["events"][0]["audio_url"],
				headers={"X-Attendance-Sign-Key": self.key, "X-Frappe-Site-Name": frappe.local.site},
			)
			with urlopen(audio_request, timeout=10) as response:
				self.assertEqual(response.headers.get_content_type(), "audio/wav")
				self.assertEqual(response.read(), self.wav)
		finally:
			server.shutdown()
			server.server_close()
			thread.join()
			frappe.db.delete("Employee Checkin", {"name": "sign-http-committed"})
			frappe.delete_doc("QR Checkin Location", self.location, force=True)
			frappe.db.commit()
