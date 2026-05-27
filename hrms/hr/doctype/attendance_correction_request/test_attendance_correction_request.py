from datetime import date, datetime, timedelta
from unittest.mock import call, patch

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

	def test_submit_api_creates_pending_request_for_current_employee(self):
		from hrms.api.attendance_correction import submit_attendance_correction_request

		employee, _shift = self.make_request_employee("attendance-correction-api-submit@example.com")
		frappe.set_user("attendance-correction-api-submit@example.com")

		result = submit_attendance_correction_request(
			{
				"attendance_date": "2026-05-20",
				"request_type": "Forgot Check-in",
				"requested_log_type": "IN",
				"requested_time": "2026-05-20 09:05:00",
				"reason": "Forgot to scan",
			}
		)

		frappe.set_user("Administrator")
		doc = frappe.get_doc("Attendance Correction Request", result["name"])
		self.assertEqual(doc.employee, employee)
		self.assertEqual(doc.status, "Pending")

	def test_current_employee_api_returns_active_employee_for_session_user(self):
		from hrms.api.attendance_correction import get_current_employee

		employee, _shift = self.make_request_employee("attendance-correction-current-employee@example.com")

		frappe.set_user("attendance-correction-current-employee@example.com")
		self.assertEqual(get_current_employee(), employee)
		frappe.set_user("Administrator")

	def test_submit_api_accepts_json_payload_and_refetches_resources(self):
		from hrms.api.attendance_correction import submit_attendance_correction_request

		employee, _shift = self.make_request_employee("attendance-correction-api-json@example.com")

		frappe.set_user("attendance-correction-api-json@example.com")
		with patch("hrms.refetch_resource") as refetch_resource:
			result = submit_attendance_correction_request(
				"""
				{
					"attendance_date": "2026-05-20",
					"request_type": "Forgot Check-out",
					"requested_log_type": "OUT",
					"requested_time": "2026-05-20 18:05:00",
					"reason": "Forgot to scan"
				}
				"""
			)
		frappe.set_user("Administrator")

		doc = frappe.get_doc("Attendance Correction Request", result["name"])
		self.assertEqual(doc.employee, employee)
		refetch_resource.assert_has_calls(
			[
				call("hrms:my_attendance_correction_requests", "attendance-correction-api-json@example.com"),
				call("hrms:pending_attendance_correction_approvals", "test@example.com"),
				call("hrms:attendance_correction_approval_count", "test@example.com"),
			]
		)

	def test_pending_approvals_api_returns_only_current_approver_requests(self):
		from hrms.api.attendance_correction import get_pending_attendance_correction_approvals

		employee, _shift = self.make_request_employee("attendance-correction-api-approval@example.com")
		request = self.make_pending_request(
			employee,
			"Forgot Check-out",
			"OUT",
			"2026-05-20 18:05:00",
		)

		frappe.set_user("test@example.com")
		results = get_pending_attendance_correction_approvals()
		frappe.set_user("Administrator")

		self.assertIn(request.name, {item["name"] for item in results})

	def test_pending_approvals_api_excludes_other_approvers(self):
		from hrms.api.attendance_correction import get_pending_attendance_correction_approvals

		employee, _shift = self.make_request_employee("attendance-correction-api-current-approver@example.com")
		current_request = self.make_pending_request(
			employee,
			"Forgot Check-out",
			"OUT",
			"2026-05-20 18:05:00",
		)
		other_employee, _other_shift = self.make_request_employee(
			"attendance-correction-api-other-approver@example.com"
		)
		frappe.db.set_value("Employee", other_employee, "attendance_correction_approver", "test1@example.com")
		other_request = self.make_pending_request(
			other_employee,
			"Forgot Check-in",
			"IN",
			"2026-05-20 09:05:00",
		)

		frappe.set_user("test@example.com")
		results = get_pending_attendance_correction_approvals()
		frappe.set_user("Administrator")
		result_names = {item["name"] for item in results}

		self.assertIn(current_request.name, result_names)
		self.assertNotIn(other_request.name, result_names)

	def test_pending_approvals_api_uses_explicit_approver_query(self):
		from hrms.api.attendance_correction import get_pending_attendance_correction_approvals

		with (
			patch.object(frappe.session, "user", "test@example.com"),
			patch("frappe.get_all", return_value=[{"name": "HR-ACR-API"}]) as get_all,
		):
			self.assertEqual(get_pending_attendance_correction_approvals(), [{"name": "HR-ACR-API"}])

		get_all.assert_called_once()
		self.assertEqual(
			get_all.call_args.kwargs["filters"],
			{"approver": "test@example.com", "status": "Pending"},
		)

	def test_my_requests_api_returns_only_current_employee_requests(self):
		from hrms.api.attendance_correction import get_my_attendance_correction_requests

		employee, _shift = self.make_request_employee("attendance-correction-api-mine@example.com")
		my_request = self.make_pending_request(
			employee,
			"Forgot Check-in",
			"IN",
			"2026-05-20 09:05:00",
		)
		other_employee, _other_shift = self.make_request_employee("attendance-correction-api-not-mine@example.com")
		other_request = self.make_pending_request(
			other_employee,
			"Forgot Check-out",
			"OUT",
			"2026-05-20 18:05:00",
		)

		frappe.set_user("attendance-correction-api-mine@example.com")
		results = get_my_attendance_correction_requests()
		frappe.set_user("Administrator")
		result_names = {item["name"] for item in results}

		self.assertIn(my_request.name, result_names)
		self.assertNotIn(other_request.name, result_names)

	def test_approval_count_api_counts_only_current_approver(self):
		from hrms.api.attendance_correction import get_attendance_correction_approval_count

		with patch.object(frappe.session, "user", "Administrator"):
			self.assertEqual(get_attendance_correction_approval_count(), 0)

		with (
			patch.object(frappe.session, "user", "test@example.com"),
			patch("frappe.db.count", return_value=3) as count,
		):
			self.assertEqual(get_attendance_correction_approval_count(), 3)

		count.assert_called_once_with(
			"Attendance Correction Request",
			{"approver": "test@example.com", "status": "Pending"},
		)

	def test_detail_api_returns_request_for_assigned_approver(self):
		from hrms.api.attendance_correction import get_attendance_correction_request

		doc = frappe._dict(
			name="HR-ACR-DETAIL",
			employee="HR-EMP-00001",
			employee_name="Test Employee",
			attendance_date="2026-05-20",
			request_type="Forgot Check-out",
			requested_log_type="OUT",
			requested_time="2026-05-20 18:05:00",
			original_checkin=None,
			reason="Forgot to scan",
			status="Pending",
			approver="approver@example.com",
			rejection_reason=None,
			created_checkin=None,
			updated_checkin=None,
			result_attendance=None,
			apply_error=None,
			creation="2026-05-20 18:10:00",
			owner="employee@example.com",
		)

		with (
			patch.object(frappe.session, "user", "approver@example.com"),
			patch("frappe.get_doc", return_value=doc),
			patch("frappe.get_roles", return_value=[]),
			patch("frappe.db.get_value", return_value=None),
			patch(
				"hrms.api.attendance_correction.build_attendance_correction_context",
				return_value={"employee": "HR-EMP-00001", "attendance_date": "2026-05-20"},
			) as build_context,
		):
			result = get_attendance_correction_request("HR-ACR-DETAIL")

		self.assertEqual(result["name"], "HR-ACR-DETAIL")
		self.assertEqual(result["reason"], "Forgot to scan")
		self.assertEqual(result["context"]["employee"], "HR-EMP-00001")
		build_context.assert_called_once_with("HR-EMP-00001", "2026-05-20")

	def test_detail_api_rejects_unrelated_employee(self):
		from hrms.api.attendance_correction import get_attendance_correction_request

		doc = frappe._dict(
			name="HR-ACR-DETAIL",
			employee="HR-EMP-00001",
			approver="approver@example.com",
		)

		with (
			patch.object(frappe.session, "user", "other@example.com"),
			patch("frappe.get_doc", return_value=doc),
			patch("frappe.get_roles", return_value=[]),
			patch("frappe.db.get_value", return_value="HR-EMP-OTHER"),
		):
			self.assertRaises(frappe.PermissionError, get_attendance_correction_request, "HR-ACR-DETAIL")

	def test_approve_and_reject_api_delegate_to_doctype_methods(self):
		from hrms.api.attendance_correction import (
			approve_attendance_correction_request,
			reject_attendance_correction_request,
		)

		class FakeAttendanceCorrectionRequest:
			name = "HR-ACR-API"
			status = "Pending"
			result_attendance = "HR-ATT-API"
			approver = "test@example.com"

			def approve(self, user):
				self.approved_user = user
				self.status = "Applied"

			def reject(self, reason, user):
				self.rejection_reason = reason
				self.rejected_user = user
				self.status = "Rejected"

		doc = FakeAttendanceCorrectionRequest()
		with (
			patch.object(frappe.session, "user", "test@example.com"),
			patch("frappe.get_doc", return_value=doc) as get_doc,
			patch("hrms.refetch_resource"),
		):
			approve_result = approve_attendance_correction_request("HR-ACR-API")
			reject_result = reject_attendance_correction_request("HR-ACR-API", "Missing details")

		get_doc.assert_has_calls(
			[
				call("Attendance Correction Request", "HR-ACR-API"),
				call("Attendance Correction Request", "HR-ACR-API"),
			]
		)
		self.assertEqual(doc.approved_user, "test@example.com")
		self.assertEqual(approve_result["attendance"], "HR-ATT-API")
		self.assertEqual(doc.rejection_reason, "Missing details")
		self.assertEqual(doc.rejected_user, "test@example.com")
		self.assertEqual(reject_result["status"], "Rejected")

	def test_approve_and_reject_api_refetch_resources(self):
		from hrms.api.attendance_correction import (
			approve_attendance_correction_request,
			reject_attendance_correction_request,
		)

		class FakeAttendanceCorrectionRequest:
			name = "HR-ACR-API"
			status = "Pending"
			result_attendance = "HR-ATT-API"
			owner = "employee@example.com"
			approver = "assigned-approver@example.com"

			def approve(self, user):
				self.status = "Applied"

			def reject(self, reason, user):
				self.status = "Rejected"

		doc = FakeAttendanceCorrectionRequest()
		with (
			patch.object(frappe.session, "user", "hr-manager@example.com"),
			patch("frappe.get_doc", return_value=doc),
			patch("hrms.refetch_resource") as refetch_resource,
		):
			approve_attendance_correction_request("HR-ACR-API")
			reject_attendance_correction_request("HR-ACR-API", "Missing details")

		refetch_resource.assert_has_calls(
			[
				call("hrms:my_attendance_correction_requests", "employee@example.com"),
				call("hrms:pending_attendance_correction_approvals", "assigned-approver@example.com"),
				call("hrms:attendance_correction_approval_count", "assigned-approver@example.com"),
				call("hrms:my_attendance_correction_requests", "employee@example.com"),
				call("hrms:pending_attendance_correction_approvals", "assigned-approver@example.com"),
				call("hrms:attendance_correction_approval_count", "assigned-approver@example.com"),
			]
		)

	def test_context_api_rejects_other_employee_for_regular_employee(self):
		from hrms.api.attendance_correction import get_attendance_correction_context

		self.make_request_employee("attendance-correction-api-context-owner@example.com")
		other_employee, _shift = self.make_request_employee("attendance-correction-api-context-other@example.com")

		frappe.set_user("attendance-correction-api-context-owner@example.com")
		self.assertRaises(
			frappe.PermissionError,
			get_attendance_correction_context,
			"2026-05-20",
			other_employee,
		)
		frappe.set_user("Administrator")

	def test_context_api_allows_admin_hr_manager_and_approver_for_other_employee(self):
		from hrms.api.attendance_correction import get_attendance_correction_context

		employee, _shift = self.make_request_employee("attendance-correction-api-allowed-context@example.com")

		with patch.object(frappe.session, "user", "Administrator"):
			self.assertEqual(get_attendance_correction_context("2026-05-20", employee)["employee"], employee)

		with (
			patch.object(frappe.session, "user", "hr-manager@example.com"),
			patch("frappe.get_roles", return_value=["HR Manager"]),
		):
			self.assertEqual(get_attendance_correction_context("2026-05-20", employee)["employee"], employee)

		with (
			patch.object(frappe.session, "user", "test@example.com"),
			patch("frappe.get_roles", return_value=[]),
		):
			self.assertEqual(get_attendance_correction_context("2026-05-20", employee)["employee"], employee)

	def test_context_access_uses_direct_employee_approver_before_department(self):
		from hrms.api.attendance_correction import is_attendance_correction_approver

		with (
			patch("frappe.db.get_value", return_value=("direct@example.com", "Sales - TC")),
			patch("frappe.db.exists", return_value="Department Approver") as exists,
		):
			self.assertTrue(is_attendance_correction_approver("HR-EMP-00001", "direct@example.com"))
			self.assertFalse(is_attendance_correction_approver("HR-EMP-00001", "dept@example.com"))

		exists.assert_not_called()

	def test_context_access_allows_only_first_department_approver(self):
		from hrms.api.attendance_correction import is_attendance_correction_approver

		with (
			patch("frappe.db.get_value", return_value=(None, "Sales - TC")),
			patch("frappe.db.exists", return_value=None) as exists,
		):
			self.assertFalse(is_attendance_correction_approver("HR-EMP-00001", "second@example.com"))

		exists.assert_called_once_with(
			"Department Approver",
			{
				"parent": "Sales - TC",
				"parentfield": "attendance_correction_approver",
				"approver": "second@example.com",
				"idx": 1,
			},
		)

	def test_context_api_returns_shift_name_and_single_attendance(self):
		from hrms.api.attendance_correction import get_attendance_correction_context

		employee, shift = self.make_request_employee("attendance-correction-api-context@example.com")
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": "2026-05-20 09:00:00",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": "2026-05-20",
				"status": "Present",
				"working_hours": 8,
				"shift": shift.name,
			}
		).insert(ignore_permissions=True).submit()

		context = get_attendance_correction_context("2026-05-20", employee)

		self.assertEqual(context["employee"], employee)
		self.assertEqual(context["attendance_date"], "2026-05-20")
		self.assertEqual(context["shift"], shift.name)
		self.assertEqual(len(context["checkins"]), 1)
		self.assertEqual(context["checkins"][0]["log_type"], "IN")
		self.assertIsInstance(context["attendance"], dict)
		self.assertEqual(context["attendance"]["status"], "Present")

	def test_context_api_ignores_expired_shift_assignments(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.api.attendance_correction import get_attendance_correction_context
		from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type

		employee = make_employee("attendance-correction-api-expired-shift@example.com", company="_Test Company")
		frappe.db.set_value("Employee", employee, "attendance_correction_approver", "test@example.com")
		expired_shift = setup_shift_type(shift_type="Attendance Correction Expired Shift")
		make_shift_assignment(expired_shift.name, employee, "2026-05-01", "2026-05-10")

		context = get_attendance_correction_context("2026-05-20", employee)

		self.assertNotEqual(context["shift"], expired_shift.name)

	def test_context_api_includes_next_day_checkins_for_overnight_shift(self):
		from erpnext.setup.doctype.employee.test_employee import make_employee

		from hrms.api.attendance_correction import get_attendance_correction_context
		from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type

		employee = make_employee("attendance-correction-api-overnight@example.com", company="_Test Company")
		frappe.db.set_value("Employee", employee, "attendance_correction_approver", "test@example.com")
		shift = setup_shift_type(
			shift_type="Attendance Correction Overnight Context Shift",
			start_time="22:00:00",
			end_time="06:00:00",
		)
		make_shift_assignment(shift.name, employee, "2026-05-20")
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "OUT",
				"time": "2026-05-21 06:00:00",
			}
		).insert(ignore_permissions=True)

		context = get_attendance_correction_context("2026-05-20", employee)

		self.assertIn(checkin.name, {item["name"] for item in context["checkins"]})

	def test_attendance_correction_list_limit_is_bounded(self):
		from hrms.api.attendance_correction import _normalize_limit

		self.assertEqual(_normalize_limit(None), 20)
		self.assertEqual(_normalize_limit("5"), 5)

		for limit in (0, -1, 101, "invalid"):
			self.assertRaises(frappe.ValidationError, _normalize_limit, limit)

	def test_duplicate_pending_request_is_not_allowed_for_same_employee_date_and_log_type(self):
		employee, _shift = self.make_request_employee("attendance-correction-duplicate@example.com")
		self.make_pending_request(
			employee,
			"Forgot Check-in",
			"IN",
			"2026-05-20 09:05:00",
		)

		duplicate = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": employee,
				"attendance_date": "2026-05-20",
				"request_type": "Forgot Check-in",
				"requested_log_type": "IN",
				"requested_time": "2026-05-20 09:10:00",
				"reason": "Forgot to punch again",
				"status": "Pending",
			}
		)

		self.assertRaises(frappe.ValidationError, duplicate.insert, ignore_permissions=True)

	def test_correct_checkin_pending_requests_are_distinct_by_original_checkin(self):
		employee, _shift = self.make_request_employee("attendance-correction-original-checkin@example.com")
		first_checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": "2026-05-20 09:00:00",
			}
		).insert(ignore_permissions=True)
		second_checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": "2026-05-20 09:30:00",
			}
		).insert(ignore_permissions=True)
		self.make_pending_request(
			employee,
			"Correct Checkin Time",
			"IN",
			"2026-05-20 09:05:00",
			original_checkin=first_checkin.name,
		)

		second_request = self.make_pending_request(
			employee,
			"Correct Checkin Time",
			"IN",
			"2026-05-20 09:35:00",
			original_checkin=second_checkin.name,
		)

		self.assertEqual(second_request.original_checkin, second_checkin.name)

	def test_correct_checkin_pending_request_is_unique_by_original_checkin(self):
		employee, _shift = self.make_request_employee("attendance-correction-same-original-checkin@example.com")
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "IN",
				"time": "2026-05-20 09:00:00",
			}
		).insert(ignore_permissions=True)
		self.make_pending_request(
			employee,
			"Correct Checkin Time",
			"IN",
			"2026-05-20 09:05:00",
			original_checkin=checkin.name,
		)

		duplicate = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": employee,
				"attendance_date": "2026-05-20",
				"request_type": "Correct Checkin Time",
				"requested_log_type": "OUT",
				"requested_time": "2026-05-20 18:05:00",
				"original_checkin": checkin.name,
				"reason": "Correct same checkin again",
				"status": "Pending",
			}
		)

		self.assertRaises(frappe.ValidationError, duplicate.insert, ignore_permissions=True)

	def test_correct_checkin_duplicate_is_unique_by_original_checkin_across_dates(self):
		employee, _shift = self.make_request_employee("attendance-correction-same-original-cross-date@example.com")
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": "OUT",
				"time": "2026-05-20 18:00:00",
			}
		).insert(ignore_permissions=True)
		self.make_pending_request(
			employee,
			"Correct Checkin Time",
			"OUT",
			"2026-05-20 18:05:00",
			original_checkin=checkin.name,
		)
		duplicate = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": employee,
				"attendance_date": "2026-05-21",
				"request_type": "Correct Checkin Time",
				"requested_log_type": "OUT",
				"requested_time": "2026-05-21 18:05:00",
				"original_checkin": checkin.name,
				"reason": "Correct same checkin on another date",
				"status": "Pending",
			}
		)

		self.assertRaises(frappe.ValidationError, duplicate.insert, ignore_permissions=True)

	def test_submit_api_rejects_invalid_json_payload(self):
		from hrms.api.attendance_correction import submit_attendance_correction_request

		self.assertRaises(frappe.ValidationError, submit_attendance_correction_request, "{invalid")

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
			"2026-05-20",
			commit=False,
		)

	def test_recalculate_attendance_converts_date_object_to_string(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": "HR-EMP-00001",
				"attendance_date": date(2026, 5, 20),
			}
		)

		with patch(
			"hrms.hr.doctype.employee_checkin.employee_checkin_utils.recalculate_attendance",
			return_value={"status": "success", "attendance": "HR-ATT-00001"},
		) as recalculate_attendance:
			self.assertEqual(request.recalculate_attendance_for_request(), "HR-ATT-00001")

		recalculate_attendance.assert_called_once_with(
			request.employee,
			"2026-05-20",
			commit=False,
		)

	def test_recalculate_attendance_runs_as_administrator_and_restores_user(self):
		request = frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": "HR-EMP-00001",
				"attendance_date": "2026-05-20",
			}
		)

		with (
			patch.object(frappe.session, "user", "approver@example.com"),
			patch("frappe.set_user") as set_user,
			patch(
				"hrms.hr.doctype.employee_checkin.employee_checkin_utils.recalculate_attendance",
				return_value={"status": "success", "attendance": "HR-ATT-00001"},
			),
		):
			self.assertEqual(request.recalculate_attendance_for_request(), "HR-ATT-00001")

		set_user.assert_has_calls([call("Administrator"), call("approver@example.com")])

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
