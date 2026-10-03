from datetime import date, datetime
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import getdate

import hrms.api as api
from hrms.api import build_pwa_attendance_anomaly, group_pwa_checkins_by_attendance_date


def checkin(day, hour, minute, log_type, attendance=None):
	return frappe._dict(
		time=datetime(day.year, day.month, day.day, hour, minute),
		log_type=log_type,
		attendance=attendance,
	)


class TestPwaAttendanceAnomalies(unittest.TestCase):
	def setUp(self):
		self.today = date(2026, 5, 27)
		self.history_day = date(2026, 5, 25)

	def assert_codes(self, logs, expected_codes):
		result = build_pwa_attendance_anomaly(self.history_day, logs, today=self.today)
		self.assertEqual(result["codes"], expected_codes)
		self.assertEqual(result["has_issue"], bool(expected_codes))

	def test_history_single_in_is_missing_checkout(self):
		self.assert_codes([checkin(self.history_day, 9, 0, "IN")], ["missing_checkout"])

	def test_history_single_out_is_missing_checkin(self):
		self.assert_codes([checkin(self.history_day, 18, 0, "OUT")], ["missing_checkin"])

	def test_history_in_out_in_is_missing_checkout(self):
		self.assert_codes(
			[
				checkin(self.history_day, 9, 0, "IN"),
				checkin(self.history_day, 12, 0, "OUT"),
				checkin(self.history_day, 13, 0, "IN"),
			],
			["missing_checkout"],
		)

	def test_history_out_in_is_invalid_sequence(self):
		self.assert_codes(
			[
				checkin(self.history_day, 9, 0, "OUT"),
				checkin(self.history_day, 18, 0, "IN"),
			],
			["invalid_sequence"],
		)

	def test_history_repeated_same_type_is_invalid_sequence(self):
		self.assert_codes(
			[
				checkin(self.history_day, 9, 0, "IN"),
				checkin(self.history_day, 10, 0, "IN"),
			],
			["invalid_sequence"],
		)
		self.assert_codes(
			[
				checkin(self.history_day, 9, 0, "OUT"),
				checkin(self.history_day, 10, 0, "OUT"),
			],
			["invalid_sequence"],
		)

	def test_history_multi_segment_complete_chain_is_normal(self):
		self.assert_codes(
			[
				checkin(self.history_day, 9, 0, "IN"),
				checkin(self.history_day, 12, 0, "OUT"),
				checkin(self.history_day, 13, 0, "IN"),
				checkin(self.history_day, 18, 0, "OUT"),
			],
			[],
		)

	def test_history_no_checkins_is_normal_rest_or_empty_day(self):
		self.assert_codes([], [])

	def test_today_single_in_is_not_marked_missing_checkout(self):
		result = build_pwa_attendance_anomaly(
			self.today,
			[checkin(self.today, 9, 0, "IN")],
			today=self.today,
		)
		self.assertEqual(result["codes"], [])
		self.assertFalse(result["has_issue"])

	def test_untyped_odd_alternating_logs_are_missing_checkout(self):
		result = build_pwa_attendance_anomaly(
			self.history_day,
			[
				frappe._dict(time=datetime(2026, 5, 25, 9, 0), log_type=None),
				frappe._dict(time=datetime(2026, 5, 25, 12, 0), log_type=None),
				frappe._dict(time=datetime(2026, 5, 25, 13, 0), log_type=None),
			],
			today=self.today,
		)
		self.assertEqual(result["codes"], ["missing_checkout"])

	def test_groups_linked_overnight_checkout_to_attendance_date(self):
		attendance_day = date(2026, 5, 25)
		next_day = date(2026, 5, 26)
		grouped = group_pwa_checkins_by_attendance_date(
			[
				checkin(attendance_day, 21, 0, "IN", attendance="ATT-001"),
				checkin(next_day, 0, 30, "OUT", attendance="ATT-001"),
			],
			{"ATT-001": attendance_day},
			attendance_day,
			next_day,
		)

		self.assertEqual([log.log_type for log in grouped[attendance_day]], ["IN", "OUT"])
		self.assertNotIn(next_day, grouped)

	def test_groups_unlinked_checkins_by_their_own_date(self):
		attendance_day = date(2026, 5, 25)
		grouped = group_pwa_checkins_by_attendance_date(
			[checkin(attendance_day, 9, 0, "IN")],
			{},
			attendance_day,
			attendance_day,
		)

		self.assertEqual([log.log_type for log in grouped[attendance_day]], ["IN"])

	def test_unsettled_overnight_checkout_belongs_to_its_shift_date(self):
		log = checkin(self.today, 0, 30, "OUT")
		log.shift_start = datetime(2026, 5, 26, 6, 0)
		grouped = group_pwa_checkins_by_attendance_date(
			[log], {}, date(2026, 5, 26), self.today
		)
		self.assertNotIn(self.today, grouped)
		self.assertEqual(grouped[date(2026, 5, 26)], [log])


class TestPwaTodayAttendanceStatus(unittest.TestCase):
	def setUp(self):
		self.today = date(2026, 9, 30)

	def calendar_events(self, logs=(), attendance=None, holidays=()):
		with (
			patch("hrms.api.getdate", side_effect=lambda value=None: getdate(value) if value else self.today),
			patch("hrms.api.get_holidays_for_calendar", return_value=list(holidays)),
			patch("hrms.api.get_attendance_for_calendar", return_value=attendance or {}),
			patch("hrms.api.get_checkins_for_attendance_calendar", return_value={self.today: list(logs)}),
			patch("hrms.api.get_shifts_for_calendar", return_value={}),
		):
			return api.get_attendance_calendar_events("2026-09-29", "2026-10-01", employee="_Test Employee")

	def test_today_without_checkins_is_not_blank(self):
		event = self.calendar_events().get("2026-09-30", {})
		self.assertEqual(event.get("checkin_status"), "not_checked_in")
		self.assertNotIn("attendance", event)
		self.assertNotIn("working_hours", event)

	def test_latest_checkin_controls_status_after_repeated_returns(self):
		logs = []
		for hour, minute, log_type, status in (
			(9, 0, "IN", "working"),
			(12, 0, "OUT", "checked_out"),
			(13, 0, "IN", "working"),
			(18, 0, "OUT", "checked_out"),
		):
			logs.append(checkin(self.today, hour, minute, log_type))
			with self.subTest(log_type=log_type, hour=hour):
				event = self.calendar_events(reversed(logs)).get("2026-09-30", {})
				self.assertEqual(event.get("checkin_status"), status)
				self.assertEqual(event.get("in_time"), "09:00")
				self.assertEqual(event.get("out_time"), f"{hour:02}:{minute:02}" if log_type == "OUT" else None)
				self.assertNotIn("attendance", event)
				self.assertNotIn("working_hours", event)

	def test_untyped_checkins_keep_alternating_in_out_status(self):
		logs = [checkin(self.today, 9, 0, None)]
		self.assertEqual(self.calendar_events(logs).get("2026-09-30", {}).get("checkin_status"), "working")
		logs.append(checkin(self.today, 18, 0, None))
		self.assertEqual(self.calendar_events(logs).get("2026-09-30", {}).get("checkin_status"), "checked_out")

	def test_current_status_does_not_create_historical_or_future_events(self):
		events = self.calendar_events([checkin(self.today, 9, 0, "IN")])
		self.assertNotIn("2026-09-29", events)
		self.assertNotIn("2026-10-01", events)

	def test_submitted_attendance_keeps_its_final_hours(self):
		attendance = {self.today: {
			"name": "ATT-001", "status": "Present", "in_time": "09:00", "out_time": "18:00", "working_hours": 8,
		}}
		event = self.calendar_events(attendance=attendance)["2026-09-30"]
		self.assertEqual(event["attendance"], "Present")
		self.assertEqual(event["working_hours"], 8)
		self.assertNotIn("checkin_status", event)


if __name__ == "__main__":
	unittest.main()
