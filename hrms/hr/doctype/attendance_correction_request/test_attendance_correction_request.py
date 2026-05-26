from datetime import datetime, timedelta
from unittest.mock import patch

import frappe

from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
	AttendanceCorrectionRequest,
)
from hrms.tests.utils import HRMSTestSuite


class TestAttendanceCorrectionRequest(HRMSTestSuite):
	def test_doctype_has_required_fields_and_permissions(self):
		meta = frappe.get_meta("Attendance Correction Request")
		fieldnames = {field.fieldname for field in meta.fields}

		for fieldname in {
			"employee",
			"employee_name",
			"department",
			"company",
			"attendance_date",
			"shift",
			"request_type",
			"requested_log_type",
			"requested_time",
			"original_checkin",
			"reason",
			"status",
			"approver",
			"approved_by",
			"approved_on",
			"rejection_reason",
			"created_checkin",
			"updated_checkin",
			"result_attendance",
			"apply_error",
		}:
			self.assertIn(fieldname, fieldnames)

		self.assertEqual(meta.autoname, "HR-ACR-.YY.-.MM.-.#####")
		self.assertEqual(meta.track_changes, 1)
		self.assertEqual(meta.title_field, "employee_name")

		employee_perm = next(perm for perm in meta.permissions if perm.role == "Employee")
		hr_manager_perm = next(perm for perm in meta.permissions if perm.role == "HR Manager")
		system_manager_perm = next(perm for perm in meta.permissions if perm.role == "System Manager")

		self.assertEqual(employee_perm.create, 1)
		self.assertEqual(employee_perm.read, 1)
		self.assertEqual(employee_perm.write, 1)
		self.assertEqual(employee_perm.delete, 1)
		self.assertEqual(employee_perm.submit, 0)
		self.assertEqual(hr_manager_perm.read, 1)
		self.assertEqual(hr_manager_perm.write, 1)
		self.assertEqual(hr_manager_perm.delete, 1)
		self.assertEqual(hr_manager_perm.submit, 1)
		self.assertEqual(hr_manager_perm.cancel, 1)
		self.assertEqual(hr_manager_perm.amend, 1)
		self.assertEqual(system_manager_perm.read, 1)
		self.assertEqual(system_manager_perm.write, 1)
		self.assertEqual(system_manager_perm.delete, 1)
		self.assertEqual(system_manager_perm.submit, 1)
		self.assertEqual(system_manager_perm.cancel, 1)
		self.assertEqual(system_manager_perm.amend, 1)

	def test_status_result_changes_require_internal_flag(self):
		status_changes = (
			("Pending", "Applied"),
			("Pending", "Apply Failed"),
			("Pending", "Rejected"),
			("Applied", "Pending"),
			("Apply Failed", "Pending"),
			("Rejected", "Draft"),
		)

		for old_status, new_status in status_changes:
			doc = frappe.get_doc({"doctype": "Attendance Correction Request", "status": new_status})

			with (
				patch.object(AttendanceCorrectionRequest, "is_new", return_value=False),
				patch.object(AttendanceCorrectionRequest, "has_value_changed", return_value=True),
				patch.object(
					AttendanceCorrectionRequest,
					"get_doc_before_save",
					return_value=frappe._dict(status=old_status),
				),
			):
				doc.flags.allow_status_change = False

				self.assertRaises(frappe.ValidationError, doc.validate_status_transition)

				doc.flags.allow_status_change = True
				doc.validate_status_transition()

	def test_new_requests_can_only_start_as_draft_or_pending(self):
		with patch.object(AttendanceCorrectionRequest, "is_new", return_value=True):
			for status in ("Draft", "Pending"):
				doc = frappe.get_doc({"doctype": "Attendance Correction Request", "status": status})
				doc.validate_status_transition()

			doc = frappe.get_doc({"doctype": "Attendance Correction Request"})
			doc.validate_status_transition()
			self.assertEqual(doc.status, "Draft")

			for status in ("Applied", "Apply Failed", "Rejected"):
				doc = frappe.get_doc({"doctype": "Attendance Correction Request", "status": status})
				self.assertRaises(frappe.ValidationError, doc.validate_status_transition)

	def test_resolve_approver_from_employee_field(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
			get_attendance_correction_approver,
		)

		employee = make_employee(
			"attendance-correction-employee-approver@example.com",
			company="_Test Company",
		)
		frappe.db.set_value(
			"Employee",
			employee,
			"attendance_correction_approver",
			"test@example.com",
		)

		self.assertEqual(get_attendance_correction_approver(employee), "test@example.com")

	def test_resolve_approver_from_department_fallback(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
			get_attendance_correction_approver,
		)

		department = frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": "Attendance Correction Department",
				"company": "_Test Company",
			}
		).insert(ignore_if_duplicate=True)

		employee = make_employee(
			"attendance-correction-department-approver@example.com",
			company="_Test Company",
			department=department.name,
		)
		department.append(
			"attendance_correction_approver",
			{"approver": "test@example.com"},
		)
		department.save()

		self.assertEqual(get_attendance_correction_approver(employee), "test@example.com")

	def make_request_employee(self, email="attendance-correction-worker@example.com"):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type

		shift_name = f"Attendance Correction Shift {email}".replace("@", "-").replace(".", "-")
		employee = make_employee(email, company="_Test Company")
		frappe.db.set_value("Employee", employee, "attendance_correction_approver", "test@example.com")
		shift = setup_shift_type(
			shift_type=shift_name,
			start_time="09:00:00",
			end_time="18:00:00",
		)
		shift.process_attendance_after = "2026-05-01"
		shift.last_sync_of_checkin = "2026-05-21 00:00:00"
		shift.save()
		make_shift_assignment(shift.name, employee, "2026-05-20")
		return employee, shift

	def make_pending_request(self, employee, request_type, log_type, requested_time, original_checkin=None):
		doc = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": employee,
				"attendance_date": "2026-05-20",
				"request_type": request_type,
				"requested_log_type": log_type,
				"requested_time": requested_time,
				"original_checkin": original_checkin,
				"reason": "Forgot to punch",
				"status": "Pending",
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_approve_forgot_checkin_creates_employee_checkin(self):
		employee, _shift = self.make_request_employee("attendance-correction-in@example.com")
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "OUT",
				"time": "2026-05-20 18:05:00",
			}
		).insert(ignore_permissions=True)
		request = self.make_pending_request(
			employee,
			"Forgot Check-in",
			"IN",
			"2026-05-20 09:05:00",
		)

		request.approve("test@example.com")

		request.reload()
		self.assertEqual(request.status, "Applied")
		self.assertTrue(request.created_checkin)
		checkin = frappe.get_doc("Employee Checkin", request.created_checkin)
		self.assertEqual(checkin.employee, employee)
		self.assertEqual(checkin.log_type, "IN")
		self.assertEqual(str(checkin.time), "2026-05-20 09:05:00")
		self.assertEqual(checkin.attendance_correction_request, request.name)

	def test_approve_correct_checkin_time_updates_existing_checkin(self):
		employee, _shift = self.make_request_employee("attendance-correction-update@example.com")
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": "2026-05-20 09:00:00",
			}
		).insert(ignore_permissions=True)
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "OUT",
				"time": "2026-05-20 19:30:00",
			}
		).insert(ignore_permissions=True)
		request = self.make_pending_request(
			employee,
			"Correct Checkin Time",
			"OUT",
			"2026-05-20 18:10:00",
			original_checkin=checkin.name,
		)

		request.approve("test@example.com")

		request.reload()
		checkin.reload()
		self.assertEqual(request.status, "Applied")
		self.assertEqual(request.updated_checkin, checkin.name)
		self.assertEqual(str(checkin.time), "2026-05-20 18:10:00")
		self.assertEqual(checkin.attendance_correction_request, request.name)

	def test_reject_records_reason(self):
		employee, _shift = self.make_request_employee("attendance-correction-reject@example.com")
		request = self.make_pending_request(
			employee,
			"Forgot Check-out",
			"OUT",
			"2026-05-20 18:10:00",
		)

		request.reject("Not enough detail", "test@example.com")

		request.reload()
		self.assertEqual(request.status, "Rejected")
		self.assertEqual(request.rejection_reason, "Not enough detail")
		self.assertEqual(request.approved_by, "test@example.com")

	def test_approval_permission_uses_current_session_user(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"approver": "test@example.com",
			}
		)

		with (
			patch.object(frappe.session, "user", "employee@example.com"),
			patch("frappe.get_roles", return_value=["Employee"]),
		):
			self.assertRaises(frappe.PermissionError, request.validate_can_approve)

	def test_approve_only_allows_pending_requests(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"status": "Applied",
				"approver": "test@example.com",
			}
		)

		with (
			patch.object(frappe.session, "user", "test@example.com"),
			patch("frappe.db.savepoint") as savepoint,
			patch.object(AttendanceCorrectionRequest, "db_set") as db_set,
		):
			self.assertRaises(frappe.ValidationError, request.approve, "test@example.com")

		savepoint.assert_not_called()
		db_set.assert_not_called()
		self.assertEqual(request.status, "Applied")

	def test_reject_only_allows_pending_requests(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"status": "Applied",
				"approver": "test@example.com",
			}
		)

		with self.assertRaises(frappe.ValidationError):
			request.reject("Not enough detail", "test@example.com")

	def test_administrator_can_only_record_eligible_approval_user(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"approver": "test@example.com",
			}
		)

		with (
			patch.object(frappe.session, "user", "Administrator"),
			patch("frappe.get_roles", return_value=[]),
		):
			self.assertEqual(request.get_approval_user("test@example.com"), "test@example.com")
			self.assertRaises(
				frappe.PermissionError,
				request.get_approval_user,
				"unrelated@example.com",
			)

	def test_recalculate_attendance_does_not_commit_inside_apply(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": "HR-EMP-00001",
				"attendance_date": "2026-05-20",
			}
		)

		with patch(
			"hrms.hr.doctype.employee_checkin.employee_checkin_utils.recalculate_attendance",
			return_value={"status": "success", "attendance": "HR-ATT-00001"},
		) as recalculate_attendance:
			self.assertEqual(request.recalculate_attendance_for_request(), "HR-ATT-00001")

		recalculate_attendance.assert_called_once_with(
			request.employee,
			request.attendance_date,
			commit=False,
		)

	def test_recalculate_window_includes_next_day_for_overnight_shift(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin_utils import (
			get_attendance_recalculation_window,
		)

		shift = frappe._dict(
			{
				"start_time": timedelta(hours=22),
				"end_time": timedelta(hours=6),
				"begin_check_in_before_shift_start_time": 60,
				"allow_check_out_after_shift_end_time": 30,
			}
		)

		start_datetime, end_datetime = get_attendance_recalculation_window(shift, "2026-05-20")

		self.assertEqual(start_datetime, datetime(2026, 5, 20, 21, 0))
		self.assertEqual(end_datetime, datetime(2026, 5, 21, 6, 30))

	def test_apply_failure_rolls_back_and_persists_failed_status(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"name": "HR-ACR-TEST",
				"employee": "HR-EMP-00001",
				"status": "Pending",
				"approver": "test@example.com",
			}
		)
		request.name = "HR-ACR-TEST"

		with (
			patch.object(AttendanceCorrectionRequest, "validate_can_approve"),
			patch.object(
				AttendanceCorrectionRequest,
				"apply_correction",
				side_effect=frappe.ValidationError("Auto attendance failed"),
			),
			patch.object(AttendanceCorrectionRequest, "db_set") as db_set,
			patch("frappe.db.savepoint") as savepoint,
			patch("frappe.db.rollback") as rollback,
			patch.object(frappe.session, "user", "Administrator"),
		):
			self.assertRaises(frappe.ValidationError, request.approve, "test@example.com")

		savepoint.assert_called_once_with("attendance_correction_apply")
		rollback.assert_called_once_with(save_point="attendance_correction_apply")
		db_set.assert_called_once()
		failed_values = db_set.call_args.args[0]
		self.assertEqual(failed_values["status"], "Apply Failed")
		self.assertEqual(failed_values["approved_by"], "test@example.com")
		self.assertIn("Auto attendance failed", failed_values["apply_error"])
		self.assertTrue(db_set.call_args.kwargs["commit"])
