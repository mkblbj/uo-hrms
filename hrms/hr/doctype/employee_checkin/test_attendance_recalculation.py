from datetime import datetime
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
from hrms.hr.doctype.employee_checkin.employee_checkin_utils import recalculate_attendance
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type
from hrms.tests.utils import HRMSTestSuite


class TestAttendanceRecalculation(HRMSTestSuite):
	def make_worker(self, suffix, **shift_settings):
		employee = make_employee(
			f"attendance-settlement-{suffix}@example.com",
			company="_Test Company",
		)
		frappe.db.set_value("Employee", employee, "attendance_correction_approver", "test@example.com")
		shift = setup_shift_type(
			shift_type=f"Attendance Settlement {suffix}",
			start_time="09:00:00",
			end_time="18:00:00",
			process_attendance_after="2026-05-20",
			last_sync_of_checkin="2026-05-21 00:00:00",
		)
		shift.update(shift_settings)
		shift.save()
		make_shift_assignment(shift.name, employee, "2026-05-20")
		return employee, shift

	def make_correction(self, employee, requested_time="2026-05-20 09:00:00", log_type="IN"):
		return frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": employee,
				"attendance_date": "2026-05-20",
				"request_type": "Forgot Check-in" if log_type == "IN" else "Forgot Check-out",
				"requested_log_type": log_type,
				"requested_time": requested_time,
				"reason": "Regression test for attendance settlement",
				"status": "Pending",
			}
		).insert(ignore_permissions=True)

	def test_checkin_correction_does_not_submit_unfinished_attendance(self):
		employee, _shift = self.make_worker("unfinished")
		request = self.make_correction(employee)

		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 5, 20, 10)):
			request.approve("test@example.com")

		request.reload()
		checkin = frappe.get_doc("Employee Checkin", request.created_checkin)
		self.assertEqual(request.status, "Applied")
		self.assertFalse(request.result_attendance)
		self.assertFalse(checkin.attendance)
		self.assertEqual(checkin.skip_auto_attendance, 0)
		self.assertFalse(frappe.db.exists("Attendance", {"employee": employee, "docstatus": 1}))

	def test_real_checkout_after_daytime_correction_is_calculated_automatically(self):
		employee, shift = self.make_worker("later-checkout")
		request = self.make_correction(employee)
		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 5, 20, 10)):
			request.approve("test@example.com")
		checkout = make_checkin(employee, datetime(2026, 5, 20, 18, 11), log_type="OUT")

		shift.process_auto_attendance()

		attendance = frappe.get_doc("Attendance", {"employee": employee, "docstatus": 1})
		self.assertEqual(attendance.working_hours, 9.18)
		self.assertEqual(attendance.in_time, datetime(2026, 5, 20, 9))
		self.assertEqual(attendance.out_time, datetime(2026, 5, 20, 18, 11))
		checkout.reload()
		self.assertEqual(checkout.attendance, attendance.name)
		self.assertEqual(checkout.skip_auto_attendance, 0)

	def test_complete_punches_still_wait_until_checkout_buffer_ends(self):
		employee, _shift = self.make_worker("checkout-buffer")
		make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN")
		request = self.make_correction(employee, "2026-05-20 18:00:00", log_type="OUT")
		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 5, 20, 18, 30)):
			request.approve("test@example.com")

		self.assertEqual(request.status, "Applied")
		self.assertFalse(frappe.db.exists("Attendance", {"employee": employee, "docstatus": 1}))

	def test_overnight_correction_waits_for_next_morning_checkout(self):
		employee, shift = self.make_worker("overnight", start_time="22:00:00", end_time="06:00:00")
		request = self.make_correction(employee, "2026-05-20 22:00:00")
		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 5, 21, 0, 30)):
			request.approve("test@example.com")
		self.assertFalse(frappe.db.exists("Attendance", {"employee": employee, "docstatus": 1}))

		checkout = make_checkin(employee, datetime(2026, 5, 21, 6, 30), log_type="OUT")
		shift.last_sync_of_checkin = datetime(2026, 5, 21, 8)
		shift.save()
		shift.process_auto_attendance()

		attendance = frappe.get_doc("Attendance", {"employee": employee, "docstatus": 1})
		self.assertEqual(str(attendance.attendance_date), "2026-05-20")
		self.assertEqual(attendance.working_hours, 8.5)
		self.assertEqual(attendance.out_time, checkout.time)
		self.assertEqual(checkout.reload().skip_auto_attendance, 0)

	def test_deferred_correction_releases_premature_attendance_for_auto_calculation(self):
		employee, shift = self.make_worker("premature-attendance")
		checkin = make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN")
		old_attendance = mark_attendance_and_link_log(
			[checkin], "Present", "2026-05-20", 0, in_time=checkin.time, shift=shift.name
		)
		request = self.make_correction(employee, "2026-05-20 18:00:00", log_type="OUT")
		with patch("frappe.utils.now_datetime", return_value=datetime(2026, 5, 20, 18, 30)):
			request.approve("test@example.com")

		self.assertEqual(request.status, "Applied")
		self.assertEqual(old_attendance.reload().docstatus, 2)
		self.assertFalse(checkin.reload().attendance)
		self.assertFalse(frappe.db.exists("Attendance", {"employee": employee, "docstatus": 1}))

		shift.process_auto_attendance()
		attendance = frappe.get_doc("Attendance", {"employee": employee, "docstatus": 1})
		self.assertEqual(attendance.working_hours, 9)
		self.assertEqual(attendance.out_time, datetime(2026, 5, 20, 18))

	def test_historical_recalculation_recovers_checkout_skipped_for_duplicate_attendance(self):
		employee, shift = self.make_worker("auto-skipped")
		checkin = make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN")
		old_attendance = mark_attendance_and_link_log(
			[checkin], "Present", "2026-05-20", 0, in_time=checkin.time, shift=shift.name
		)
		checkout = make_checkin(employee, datetime(2026, 5, 20, 18), log_type="OUT")
		self.assertIsNone(
			mark_attendance_and_link_log(
				[checkout], "Present", "2026-05-20", 0, in_time=checkout.time, shift=shift.name
			)
		)
		self.assertEqual(checkout.reload().skip_auto_attendance, 1)

		result = recalculate_attendance(employee, "2026-05-20", commit=False, ignore_permissions=True)

		self.assertEqual(result["status"], "success")
		attendance = frappe.get_doc("Attendance", result["attendance"])
		self.assertEqual(attendance.working_hours, 9)
		self.assertEqual(attendance.out_time, checkout.time)
		self.assertEqual(old_attendance.reload().docstatus, 2)
		self.assertEqual(checkout.reload().skip_auto_attendance, 0)
		self.assertEqual(checkout.attendance, attendance.name)

	def test_historical_recalculation_preserves_manually_skipped_punches(self):
		employee, shift = self.make_worker("manual-skipped")
		checkin = make_checkin(employee, datetime(2026, 5, 20, 9), log_type="IN")
		checkout = make_checkin(employee, datetime(2026, 5, 20, 18), log_type="OUT")
		old_attendance = mark_attendance_and_link_log(
			[checkin, checkout],
			"Present",
			"2026-05-20",
			9,
			in_time=checkin.time,
			out_time=checkout.time,
			shift=shift.name,
		)
		ignored = make_checkin(employee, datetime(2026, 5, 20, 19), log_type="OUT")
		ignored.db_set("skip_auto_attendance", 1)

		result = recalculate_attendance(employee, "2026-05-20", commit=False, ignore_permissions=True)

		self.assertEqual(result["status"], "success")
		self.assertEqual(result["working_hours"], 9)
		self.assertEqual(old_attendance.reload().docstatus, 2)
		self.assertEqual(ignored.reload().skip_auto_attendance, 1)
		self.assertFalse(ignored.attendance)
