from datetime import datetime

import frappe

import hrms.api as api
from hrms.hr.doctype.employee_checkin import test_attendance_recalculation as fixtures
from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.tests.utils import HRMSTestSuite


class TestPwaAttendanceDayDetails(HRMSTestSuite):
	make_worker = fixtures.TestAttendanceRecalculation.make_worker
	make_split_shift_logs = fixtures.TestAttendanceRecalculation.make_split_shift_logs

	def details(self, employee):
		method = getattr(api, "get_attendance_day_details", None)
		self.assertTrue(callable(method), "The calendar needs a day-details API")
		return method("2026-05-20", employee=employee)

	def test_settled_day_returns_every_punch_and_shared_period_calculations(self):
		employee, shift, logs = self.make_split_shift_logs("calendar-settled")
		shift.process_auto_attendance()

		result = self.details(employee)

		self.assertEqual(result["attendance_date"], "2026-05-20")
		self.assertEqual([row["name"] for row in result["checkins"]], [log.name for log in logs])
		self.assertEqual([row["log_type"] for row in result["checkins"]], ["IN", "OUT", "IN", "OUT"])
		self.assertEqual([row["working_hours"] for row in result["periods"]], [3, 3.5])
		self.assertEqual(result["periods"][0]["counted_in_time"], datetime(2026, 5, 20, 9))
		self.assertEqual(result["periods"][0]["counted_out_time"], datetime(2026, 5, 20, 12))
		self.assertEqual(result["periods"][1]["counted_in_time"], datetime(2026, 5, 20, 14, 30))
		self.assertEqual(result["periods"][1]["counted_out_time"], datetime(2026, 5, 20, 18))
		self.assertEqual([row["lunch_deduction"] for row in result["periods"]], [0, 0])
		self.assertEqual(result["working_hours"], 6.5)
		self.assertEqual(result["completed_hours"], 6.5)
		self.assertTrue(result["is_settled"])
		self.assertFalse(result["has_total_difference"])

	def test_lunch_deduction_is_exposed_for_the_work_period_it_overlaps(self):
		employee, shift = self.make_worker(
			"calendar-lunch",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			enable_time_rounding=1,
			rounding_precision="30",
			enable_lunch_deduction=1,
			lunch_start="12:00:00",
			lunch_end="13:00:00",
		)
		make_checkin(employee, datetime(2026, 5, 20, 8, 55), log_type="IN")
		make_checkin(employee, datetime(2026, 5, 20, 18, 1), log_type="OUT")
		shift.process_auto_attendance()
		result = self.details(employee)
		self.assertEqual(result["periods"][0]["lunch_deduction"], 1)
		self.assertEqual(result["periods"][0]["working_hours"], 8)
		self.assertEqual(result["working_hours"], 8)

	def test_open_day_returns_punches_without_creating_final_attendance(self):
		employee, _shift = self.make_worker("calendar-open")
		log = make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN")

		result = self.details(employee)

		self.assertEqual(len(result["checkins"]), 1)
		self.assertEqual(result["periods"], [])
		self.assertEqual(result["open_period"]["in_time"], log.time)
		self.assertIsNone(result["working_hours"])
		self.assertEqual(result["completed_hours"], 0)
		self.assertFalse(result["is_settled"])
		self.assertFalse(frappe.db.exists("Attendance", {"employee": employee, "docstatus": 1}))

	def test_skipped_punch_remains_visible_and_is_not_counted(self):
		employee, shift = self.make_worker("calendar-skipped")
		logs = [
			make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN"),
			make_checkin(employee, datetime(2026, 5, 20, 12), log_type="OUT"),
		]
		mark_attendance_and_link_log(
			logs, "Present", "2026-05-20", 3, in_time=logs[0].time, out_time=logs[1].time, shift=shift.name
		)
		skipped = make_checkin(employee, datetime(2026, 5, 20, 18), log_type="OUT")
		skipped.db_set("skip_auto_attendance", 1)

		result = self.details(employee)

		self.assertEqual(len(result["checkins"]), 3)
		self.assertFalse(result["checkins"][-1]["included_in_calculation"])
		self.assertEqual(result["periods"][0]["working_hours"], 3)
		self.assertEqual(result["working_hours"], 3)

	def test_overnight_unsettled_checkout_is_grouped_with_its_shift_day(self):
		employee, _shift = self.make_worker(
			"calendar-overnight",
			start_time="22:00:00",
			end_time="06:00:00",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			enable_time_rounding=1,
			rounding_precision="30",
		)
		make_checkin(employee, datetime(2026, 5, 20, 21, 55), log_type="IN")
		make_checkin(employee, datetime(2026, 5, 21, 6, 31), log_type="OUT")

		result = self.details(employee)

		self.assertEqual(len(result["checkins"]), 2)
		self.assertEqual(result["periods"][0]["out_time"], datetime(2026, 5, 21, 6, 31))
		self.assertEqual(result["completed_hours"], 8.5)
		self.assertIsNone(result["working_hours"])

	def test_employee_can_read_own_day_but_not_another_employee(self):
		employee, _shift = self.make_worker("calendar-self")
		other, _other_shift = self.make_worker("calendar-other")
		frappe.set_user("attendance-settlement-calendar-self@example.com")
		try:
			self.assertEqual(self.details(employee)["employee"], employee)
			self.assertRaises(frappe.PermissionError, self.details, other)
		finally:
			frappe.set_user("Administrator")

	def test_settled_zero_hours_are_returned_as_zero(self):
		employee, _shift = self.make_worker("calendar-zero")
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"company": "_Test Company",
				"attendance_date": "2026-05-20",
				"status": "Absent",
				"working_hours": 0,
			}
		).submit()
		result = self.details(employee)
		self.assertTrue(result["is_settled"])
		self.assertEqual(result["working_hours"], 0)
		self.assertEqual(result["checkins"], [])

	def test_stored_total_difference_is_reported_without_rewriting_records(self):
		employee, shift, logs = self.make_split_shift_logs("calendar-difference")
		attendance = mark_attendance_and_link_log(
			logs, "Present", "2026-05-20", 8, in_time=logs[0].time, out_time=logs[-1].time, shift=shift.name
		)
		result = self.details(employee)
		self.assertEqual(result["working_hours"], 8)
		self.assertEqual(result["completed_hours"], 6.5)
		self.assertTrue(result["has_total_difference"])
		self.assertEqual(attendance.reload().working_hours, 8)

	def test_short_period_explains_zero_without_showing_a_reversed_counted_range(self):
		employee, _shift = self.make_worker(
			"calendar-short",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			enable_time_rounding=1,
			rounding_precision="30",
		)
		make_checkin(employee, datetime(2026, 5, 20, 9, 5), log_type="IN")
		make_checkin(employee, datetime(2026, 5, 20, 9, 25), log_type="OUT")
		result = self.details(employee)
		self.assertTrue(result["periods"][0]["counted_time_empty"])
		self.assertEqual(result["periods"][0]["working_hours"], 0)

	def test_stored_hours_without_punches_do_not_claim_a_calculation_difference(self):
		employee, _shift = self.make_worker("calendar-no-punches")
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"company": "_Test Company",
				"attendance_date": "2026-05-20",
				"status": "Work From Home",
				"working_hours": 8,
			}
		).submit()
		result = self.details(employee)
		self.assertEqual(result["working_hours"], 8)
		self.assertEqual(result["periods"], [])
		self.assertFalse(result["has_total_difference"])
