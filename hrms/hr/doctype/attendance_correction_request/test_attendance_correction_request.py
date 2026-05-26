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
