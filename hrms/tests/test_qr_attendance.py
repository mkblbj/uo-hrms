import unittest
from unittest.mock import patch

import frappe
from frappe.app import process_response
from frappe.utils.response import build_response

from hrms.api import qr_attendance
from hrms.www import qr_display


class TestQRAttendance(unittest.TestCase):
	def test_two_minute_codes_and_deadlines_follow_location_interval(self):
		location = frappe._dict(name="interval-door", enabled=1, qr_refresh_interval=120, description="Test")
		location.get_password = lambda _field: "test-secret"
		cases = [
			(61, 0, 120, 240),
			(119, 0, 120, 240),
			(120, 1, 240, 360),
			(239, 1, 240, 360),
			(240, 2, 360, 480),
		]
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "get_doc", return_value=location),
			patch.object(qr_attendance, "verify_display_key", return_value=True),
		):
			for now, slot, refresh_at, expires_at in cases:
				with self.subTest(now=now), patch.object(qr_attendance.time, "time", return_value=now):
					api = qr_attendance.generate_qr_token(location.name)
					page = qr_display.generate_token_for_display(location.name)
					self.assertEqual(api["token"].split("|")[1], str(slot))
					self.assertEqual(
						(api["refresh_at"], api["expires_at"], api["expires_in"]),
						(refresh_at, expires_at, 120),
					)
					self.assertEqual(api["token"], page["token"])
					self.assertEqual((page["refresh_at"], page["expires_at"]), (refresh_at, expires_at))

	def test_configured_intervals_do_not_leak_between_locations(self):
		with (
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(qr_attendance, "verify_display_key", return_value=True),
			patch.object(qr_attendance.time, "time", return_value=119),
		):
			for interval, slot, expiry in [(120, 0, 240), (30, 3, 150)]:
				location = frappe._dict(
					name="door-" + str(interval), enabled=1, qr_refresh_interval=interval, description="Test"
				)
				location.get_password = lambda _: "test-secret"
				with patch.object(frappe, "get_doc", return_value=location):
					result = qr_attendance.generate_qr_token(location.name)
				self.assertEqual((result["token"].split("|")[1], result["expires_at"]), (str(slot), expiry))

	def test_checkin_accepts_current_and_previous_configured_slot_only(self):
		class ReachedEmployeeLookup(Exception):
			pass

		location = frappe._dict(name="interval-door", enabled=1, qr_refresh_interval=120)
		location.get_password = lambda _: "test-secret"
		token = "interval-door|0|" + qr_attendance._sign("interval-door", 0, "test-secret")
		cases = [(61, True), (119, True), (120, True), (239, True), (240, False)]
		with (
			patch.object(frappe, "session", frappe._dict(user="qr-interval-test@example.com")),
			patch.object(qr_attendance, "validate_ip_whitelist"),
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "get_doc", return_value=location),
		):
			for now, accepted in cases:
				with (
					self.subTest(now=now),
					patch.object(qr_attendance.time, "time", return_value=now),
					patch.object(frappe.db, "get_value", side_effect=ReachedEmployeeLookup) as lookup,
				):
					with self.assertRaises(ReachedEmployeeLookup if accepted else frappe.ValidationError):
						qr_attendance.qr_checkin(token)
					if not accepted:
						lookup.assert_not_called()

	def test_checkin_rejects_slot_field_that_does_not_match_signature(self):
		location = frappe._dict(name="interval-door", enabled=1, qr_refresh_interval=120)
		location.get_password = lambda _: "test-secret"
		token = "interval-door|9999|" + qr_attendance._sign("interval-door", 0, "test-secret")
		with (
			patch.object(frappe, "session", frappe._dict(user="qr-interval-test@example.com")),
			patch.object(qr_attendance, "validate_ip_whitelist"),
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(frappe, "get_doc", return_value=location),
			patch.object(qr_attendance.time, "time", return_value=10),
			patch.object(frappe.db, "get_value") as lookup,
		):
			with self.assertRaises(frappe.ValidationError):
				qr_attendance.qr_checkin(token)
			lookup.assert_not_called()

	def test_generate_qr_token_uses_one_server_time_for_slot_and_deadlines(self):
		location = frappe._dict(
			name="office-10F",
			enabled=1,
			qr_refresh_interval=30,
			description="10楼办公室打卡点",
		)
		location.get_password = lambda _field: "test-secret"

		for server_time, refresh_at, expires_at in (
			(119, 120, 150),
			(120, 150, 180),
		):
			with (
				self.subTest(server_time=server_time),
				patch.object(qr_attendance.frappe.db, "exists", return_value=True),
				patch.object(qr_attendance.frappe, "get_doc", return_value=location),
				patch.object(
					qr_attendance.time, "time", side_effect=[server_time, server_time + 1]
				) as mocked_time,
			):
				frappe.local.response = frappe._dict()
				frappe.local.response_headers.clear()

				result = qr_attendance.generate_qr_token("office-10F")

				self.assertEqual(result["token"].split("|")[1], str(server_time // 30))
				self.assertEqual(result["expires_in"], 30)
				self.assertEqual(result["location"], "office-10F")
				self.assertEqual(result["description"], "10楼办公室打卡点")
				self.assertEqual(result.get("server_time"), server_time)
				self.assertEqual(result.get("refresh_at"), refresh_at)
				self.assertEqual(result.get("expires_at"), expires_at)
				self.assertEqual(mocked_time.call_count, 1)

				frappe.local.response["message"] = result
				response = build_response("json")
				process_response(response)
				self.assertEqual(
					response.headers["Cache-Control"],
					"no-store, no-cache, must-revalidate, max-age=0",
				)
				self.assertNotIn("headers", response.get_json())

	def test_get_recent_checkins_accepts_disabled_compact_mode(self):
		with patch.object(qr_attendance.frappe, "get_all", return_value=[]):
			try:
				result = qr_attendance.get_recent_checkins(compact=0)
			except TypeError as exc:
				self.fail(f"compact must be an optional API argument: {exc}")

		self.assertEqual(result, [])

	def test_get_recent_checkins_compact_requires_location(self):
		with self.assertRaises(frappe.ValidationError):
			qr_attendance.get_recent_checkins(compact=1)

	def test_get_recent_checkins_compact_returns_stable_minimal_query(self):
		checkins = [
			frappe._dict(
				name="EMP-CKIN-00002",
				log_type="OUT",
				time="2026-09-08 18:00:00",
				device_id="office-10F",
			)
		]
		with (
			patch.object(qr_attendance.frappe, "get_all", return_value=checkins) as get_all,
			patch.object(
				qr_attendance.frappe.db,
				"get_value",
				side_effect=AssertionError("compact mode must not fetch employee images"),
			),
		):
			frappe.local.response = frappe._dict()
			frappe.local.response_headers.clear()

			result = qr_attendance.get_recent_checkins(location="office-10F", limit="99", compact="1")

		self.assertEqual(result, checkins)
		get_all.assert_called_once_with(
			"Employee Checkin",
			filters={"device_id": "office-10F"},
			fields=["name", "log_type", "time", "device_id"],
			order_by="time desc, name desc",
			limit=20,
		)
		frappe.local.response["message"] = result
		response = build_response("json")
		process_response(response)
		self.assertEqual(
			response.headers["Cache-Control"],
			"no-store, no-cache, must-revalidate, max-age=0",
		)
		self.assertNotIn("headers", response.get_json())

	def test_get_recent_checkins_compact_clamps_limit_to_one(self):
		with patch.object(qr_attendance.frappe, "get_all", return_value=[]) as get_all:
			frappe.local.response = frappe._dict()

			qr_attendance.get_recent_checkins(location="office-10F", limit=0, compact=1)

		self.assertEqual(get_all.call_args.kwargs["limit"], 1)

	def test_get_recent_checkins_default_mode_keeps_existing_shape_and_avatar_lookup(self):
		checkins = [
			frappe._dict(
				employee_name="张三",
				employee="HR-EMP-00001",
				log_type="IN",
				time="2026-09-08 09:00:00",
				device_id="office-10F",
			)
		]
		with (
			patch.object(qr_attendance.frappe, "get_all", return_value=checkins) as get_all,
			patch.object(qr_attendance.frappe.db, "get_value", return_value="/files/photo.jpg"),
		):
			result = qr_attendance.get_recent_checkins(location="office-10F", limit=5)

		self.assertEqual(result[0]["employee_image"], "/files/photo.jpg")
		get_all.assert_called_once_with(
			"Employee Checkin",
			filters={"device_id": "office-10F"},
			fields=["employee_name", "employee", "log_type", "time", "device_id"],
			order_by="time desc",
			limit=5,
		)

	def test_get_employees_at_work_includes_checked_out_employees_from_today(self):
		def fake_sql(sql, params, as_dict=False):
			if "ec.log_type = 'IN'" in sql:
				return []
			return [
				frappe._dict(
					employee="HR-EMP-00001",
					employee_name="李雪莉",
					log_type="OUT",
					time="2026-06-27 18:05:00",
					location="office-10F",
					department="Production",
					designation="Staff",
					image=None,
				)
			]

		with (
			patch("frappe.utils.today", return_value="2026-06-27"),
			patch.object(qr_attendance.frappe.db, "sql", side_effect=fake_sql),
		):
			result = qr_attendance.get_employees_at_work()

		self.assertEqual(result["count"], 1)
		self.assertEqual(result["employees"][0]["employee_name"], "李雪莉")
		self.assertEqual(result["employees"][0]["attendance_status"], "off_work")
		self.assertEqual(result["employees"][0]["attendance_status_label"], "退勤済")
		self.assertEqual(result["employees"][0]["last_log_type"], "OUT")
		self.assertEqual(result["employees"][0]["checkin_time"], "18:05:00")
		self.assertEqual(result["employees"][0]["last_checkin_time"], "18:05")
		self.assertEqual(result["employees"][0]["last_checkin_location"], "office-10F")


if __name__ == "__main__":
	unittest.main()
