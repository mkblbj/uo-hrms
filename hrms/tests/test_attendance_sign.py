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
		self.doc = frappe.get_doc({"doctype": "QR Checkin Location", "location_name": self.location,
			"secret": "s" * 32, "enabled": 1, "require_display_key": 0}).insert()
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
		frappe.db.sql("""INSERT INTO `tabEmployee Checkin`
			(name, creation, modified, owner, modified_by, docstatus, idx,
			employee, employee_name, log_type, time, device_id, checkin_method)
			VALUES (%s,%s,%s,'Administrator','Administrator',0,0,%s,%s,%s,%s,%s,%s)""",
			(name, created, created, "HR-EMP-sign-example", "山田太郎", log_type,
			 created, location or self.location, method))

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

	def test_events_are_recent_committed_checkin_shape(self):
		self._row("sign-example")
		result = attendance_sign.get_events(self.location)
		self.assertEqual((result["version"], result["locale"]), (1, "ja-JP"))
		self.assertEqual(result["server_time"], self.clock.timestamp())
		self.assertEqual(result["events"], [{"id": "sign-example", "employee_id": "HR-EMP-sign-example",
			"employee_name": "山田太郎", "log_type": "IN", "time_label": "09:01",
			"created_at": self.clock.timestamp() - 1, "action_label": "出勤完了",
			"greeting": "出勤を記録しました。", "audio_url": None}])

	def test_filters_and_orders_burst(self):
		self._row("sign-z", age=3)
		self._row("sign-b", age=2, method="Passkey", log_type="OUT")
		self._row("sign-a", age=2)
		self._row("sign-stale", age=31)
		self._row("sign-correction", method="Attendance Correction")
		self._row("sign-other", location="another-door")
		self._row("sign-invalid", log_type="")
		result = attendance_sign.get_events(self.location)
		self.assertEqual([x["id"] for x in result["events"]], ["sign-z", "sign-a", "sign-b"])
		self.assertEqual(result["events"][-1]["action_label"], "退勤完了")

	def test_returns_twenty_most_recent_events(self):
		for i in range(25):
			self._row(f"sign-limit-{i:02d}", age=25-i)
		self.assertEqual([x["id"] for x in attendance_sign.get_events(self.location)["events"]],
			[f"sign-limit-{i:02d}" for i in range(5,25)])

	def test_response_is_not_cached(self):
		frappe.local.response["message"] = attendance_sign.get_events(self.location)
		from frappe.app import process_response
		response = build_response("json")
		process_response(response)
		self.assertIn("no-store", response.headers["Cache-Control"])
