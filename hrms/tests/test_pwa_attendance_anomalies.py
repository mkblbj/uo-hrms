from datetime import date, datetime
import unittest

import frappe

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


if __name__ == "__main__":
	unittest.main()
