import unittest
from datetime import datetime, timedelta

import frappe

from hrms.hr.doctype.shift_type.shift_type import ShiftType


class TestSegmentedWorkingHours(unittest.TestCase):
	def shift(self, **settings):
		values = frappe._dict(
			determine_check_in_and_check_out="Alternating entries as IN and OUT during the same shift",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			enable_time_rounding=1,
			rounding_precision="30",
			enable_lunch_deduction=1,
			lunch_start=timedelta(hours=12),
			lunch_end=timedelta(hours=13),
			enable_late_entry_marking=0,
			enable_early_exit_marking=0,
		)
		values.update(settings)
		return values

	def logs(self, times, types=None):
		return [
			frappe._dict(
				time=datetime.fromisoformat(value if " " in value else f"2026-09-11 {value}"),
				log_type=types[i] if types else ("IN" if i % 2 == 0 else "OUT"),
				shift_start=datetime(2026, 9, 11, 9),
				shift_end=datetime(2026, 9, 11, 18),
			)
			for i, value in enumerate(times)
		]

	def attendance(self, times, types=None, **settings):
		return ShiftType.get_attendance(self.shift(**settings), self.logs(times, types), 0, 0)

	def test_split_day_rounds_each_period_before_adding_hours(self):
		result = self.attendance(["08:55:00", "12:12:00", "14:27:00", "18:01:00"])
		self.assertEqual(result[0], "Present")
		self.assertEqual(result[1], 6.5)
		self.assertEqual(result[4], datetime(2026, 9, 11, 8, 55))
		self.assertEqual(result[5], datetime(2026, 9, 11, 18, 1))

	def test_seven_reported_attendances_exclude_time_between_work_periods(self):
		fixtures = (
			(["08:41:31", "18:22:53", "18:46:07", "20:04:31"], 9),
			(["08:37:15", "18:01:56", "18:22:14", "21:03:16"], 10.5),
			(["08:42:55", "18:04:43", "18:30:49", "21:34:02"], 11),
			(["08:36:11", "18:02:34", "18:37:24", "22:05:14"], 11),
			(["08:39:30", "18:06:38", "18:33:13", "20:03:12"], 9),
			(["08:47:40", "17:34:38", "18:50:10", "20:06:16"], 8.5),
			(["08:55:51", "12:12:59", "14:27:19", "17:02:21"], 5.5),
		)
		for times, hours in fixtures:
			with self.subTest(times=times):
				self.assertEqual(self.attendance(times)[1], hours)

	def test_lunch_is_only_deducted_from_the_period_that_covers_it(self):
		result = self.attendance(["08:55:00", "12:40:00", "12:50:00", "18:01:00"])
		self.assertEqual(result[1], 8)

	def test_rounding_does_not_turn_a_short_period_into_negative_hours(self):
		result = self.attendance(["09:05:00", "09:25:00", "12:55:00", "14:01:00"])
		self.assertEqual(result[1], 1)

	def test_unrounded_split_day_does_not_deduct_lunch_during_time_off(self):
		result = self.attendance(["09:00:00", "12:00:00", "14:00:00", "18:00:00"], enable_time_rounding=0)
		self.assertEqual(result[1], 7)

	def test_first_and_last_mode_keeps_its_existing_calculation(self):
		result = self.attendance(
			["08:55:00", "12:12:00", "14:27:00", "18:01:00"],
			working_hours_calculation_based_on="First Check-in and Last Check-out",
		)
		self.assertEqual(result[1], 8)

	def test_strict_log_types_only_count_complete_in_out_pairs(self):
		result = self.attendance(
			["08:00:00", "09:00:00", "09:10:00", "12:05:00", "14:20:00", "18:01:00", "18:10:00"],
			types=["OUT", "IN", "IN", "OUT", "IN", "OUT", "IN"],
			determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
		)
		self.assertEqual(result[1], 6.5)
		self.assertEqual(result[4], datetime(2026, 9, 11, 9))
		self.assertEqual(result[5], datetime(2026, 9, 11, 18, 1))

	def test_unpaired_final_checkin_is_not_used_as_a_checkout(self):
		result = self.attendance(["09:00:00", "12:05:00", "14:20:00"])
		self.assertEqual(result[1], 3)
		self.assertEqual(result[5], datetime(2026, 9, 11, 12, 5))

	def test_single_checkin_keeps_its_time_with_no_checkout(self):
		result = self.attendance(["09:00:00"])
		self.assertEqual(result[1], 0)
		self.assertEqual(result[4], datetime(2026, 9, 11, 9))
		self.assertIsNone(result[5])

	def test_overnight_period_deducts_lunch_on_the_following_day(self):
		result = self.attendance(["2026-09-11 22:00:00", "2026-09-12 14:00:00"])
		self.assertEqual(result[1], 15)

	def test_other_rounding_precisions_are_applied_to_each_period(self):
		for precision, hours in (("15", 6.5), ("30", 6), ("60", 5)):
			with self.subTest(precision=precision):
				result = self.attendance(
					["09:10:00", "12:40:00", "14:10:00", "18:10:00"], rounding_precision=precision
				)
				self.assertEqual(result[1], hours)
