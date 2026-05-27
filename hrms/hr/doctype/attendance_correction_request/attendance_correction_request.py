import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate

from hrms.hr.utils import validate_active_employee

APPLY_SAVEPOINT = "attendance_correction_apply"
ATTENDANCE_CORRECTION_MANAGER_ROLE = "Attendance Correction Manager"


class AttendanceCorrectionRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		apply_error: DF.LongText | None
		approved_by: DF.Link | None
		approved_on: DF.Datetime | None
		approver: DF.Link | None
		attendance_date: DF.Date
		company: DF.Link
		created_checkin: DF.Link | None
		department: DF.Link | None
		employee: DF.Link
		employee_name: DF.Data | None
		original_checkin: DF.Link | None
		reason: DF.SmallText | None
		rejection_reason: DF.SmallText | None
		request_type: DF.Literal["Forgot Check-in", "Forgot Check-out", "Correct Checkin Time", "Other"]
		requested_log_type: DF.Literal["", "IN", "OUT"]
		requested_time: DF.Datetime
		result_attendance: DF.Link | None
		shift: DF.Link | None
		status: DF.Literal["Draft", "Pending", "Rejected", "Applied", "Apply Failed"]
		updated_checkin: DF.Link | None
	# end: auto-generated types

	def validate(self):
		validate_active_employee(self.employee)
		self.normalize_dates()
		if not self.approver and self.status in {"Draft", "Pending"}:
			self.approver = get_attendance_correction_approver(self.employee)
		self.validate_status_transition()
		self.validate_requested_time()
		self.validate_original_checkin()
		self.validate_duplicate_pending_request()

	def normalize_dates(self):
		if self.attendance_date:
			self.attendance_date = getdate(self.attendance_date)

		if self.requested_time:
			self.requested_time = get_datetime(self.requested_time).replace(microsecond=0)

	def validate_status_transition(self):
		protected_statuses = {"Applied", "Apply Failed", "Rejected"}

		if self.is_new():
			self.status = self.status or "Draft"
			if self.status not in {"Draft", "Pending"}:
				frappe.throw(_("New Attendance Correction Request must start as Draft or Pending"))
			return

		if not self.has_value_changed("status"):
			return

		doc_before_save = self.get_doc_before_save()
		old_status = doc_before_save.status if doc_before_save else None
		if self.status in protected_statuses or old_status in protected_statuses:
			if not self.flags.allow_status_change:
				frappe.throw(_("Use the attendance correction approval actions to change this status."))

	def validate_requested_time(self):
		if not self.requested_time or not self.attendance_date:
			return

		attendance_date = getdate(self.attendance_date)
		requested_date = getdate(self.requested_time)
		next_date = getdate(add_days(attendance_date, 1))
		if requested_date not in {attendance_date, next_date}:
			frappe.throw(_("Requested Time must be on Attendance Date or the next date"))

	def validate_original_checkin(self):
		if self.request_type == "Correct Checkin Time" and not self.original_checkin:
			frappe.throw(_("Original Checkin is required for Correct Checkin Time requests"))

		if not self.original_checkin:
			return

		checkin_employee = frappe.db.get_value("Employee Checkin", self.original_checkin, "employee")
		if not checkin_employee:
			frappe.throw(_("Original Checkin {0} does not exist").format(frappe.bold(self.original_checkin)))

		if checkin_employee != self.employee:
			frappe.throw(_("Original Checkin must belong to the selected Employee"))

	def validate_duplicate_pending_request(self):
		if self.status != "Pending":
			return
		existing = frappe.db.exists(
			"Attendance Correction Request",
			self.get_duplicate_pending_filters(),
		)
		if existing:
			frappe.throw(
				_("A pending attendance correction request already exists for this date and log type.")
			)

	def get_duplicate_pending_filters(self) -> dict:
		filters = {
			"employee": self.employee,
			"request_type": self.request_type,
			"status": "Pending",
			"name": ["!=", self.name],
		}
		if self.request_type == "Correct Checkin Time":
			filters["original_checkin"] = self.original_checkin
		else:
			filters["attendance_date"] = self.attendance_date
			filters["requested_log_type"] = self.requested_log_type
		return filters

	def approve(self, approver: str | None = None):
		if self.status != "Pending":
			frappe.throw(_("Only Pending attendance correction requests can be approved."))
		self.validate_can_approve()
		approved_by = self.get_approval_user(approver)
		frappe.db.savepoint(APPLY_SAVEPOINT)
		try:
			self.apply_correction()
			self.flags.allow_status_change = True
			self.status = "Applied"
			self.approved_by = approved_by
			self.approved_on = frappe.utils.now_datetime()
			self.apply_error = None
			self.save(ignore_permissions=True)
		except Exception as exc:
			self.record_apply_failure(approved_by)
			frappe.throw(str(exc))

	def reject(self, rejection_reason: str, approver: str | None = None):
		if not rejection_reason:
			frappe.throw(_("Rejection reason is required."))
		if self.status != "Pending":
			frappe.throw(_("Only Pending attendance correction requests can be rejected."))
		self.validate_can_approve()
		self.flags.allow_status_change = True
		self.status = "Rejected"
		self.rejection_reason = rejection_reason
		self.approved_by = self.get_approval_user(approver)
		self.approved_on = frappe.utils.now_datetime()
		self.save(ignore_permissions=True)

	def validate_can_approve(self):
		current_user = frappe.session.user
		if self.can_user_approve(current_user):
			return
		frappe.throw(
			_("You are not allowed to approve this attendance correction request."),
			frappe.PermissionError,
		)

	def get_approval_user(self, approver: str | None = None) -> str:
		if approver and approver != frappe.session.user and frappe.session.user != "Administrator":
			frappe.throw(_("You cannot approve on behalf of another user."), frappe.PermissionError)
		if approver and frappe.session.user == "Administrator" and not self.can_user_approve(approver):
			frappe.throw(_("Approval user is not allowed to approve this request."), frappe.PermissionError)
		return approver or frappe.session.user

	def can_user_approve(self, user: str) -> bool:
		if user == self.approver:
			return True
		return user_can_manage_all_attendance_corrections(user) or is_attendance_correction_approver(
			self.employee, user
		)

	def record_apply_failure(self, approved_by: str):
		apply_error = frappe.get_traceback()
		frappe.db.rollback(save_point=APPLY_SAVEPOINT)
		self.db_set(
			{
				"status": "Apply Failed",
				"approved_by": approved_by,
				"approved_on": frappe.utils.now_datetime(),
				"apply_error": apply_error,
			},
			commit=True,
		)

	def apply_correction(self):
		if self.status != "Pending":
			frappe.throw(_("Only Pending attendance correction requests can be applied."))
		if self.request_type == "Correct Checkin Time":
			self.updated_checkin = self.update_original_checkin()
		else:
			self.created_checkin = self.create_corrected_checkin()
		self.result_attendance = self.recalculate_attendance_for_request()

	def create_corrected_checkin(self) -> str:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": self.requested_time,
				"log_type": self.requested_log_type,
				"device_id": "Attendance Correction",
				"skip_auto_attendance": 0,
				"attendance_correction_request": self.name,
			}
		)
		checkin.insert(ignore_permissions=True)
		return checkin.name

	def update_original_checkin(self) -> str:
		checkin = frappe.get_doc("Employee Checkin", self.original_checkin)
		checkin.time = self.requested_time
		checkin.log_type = self.requested_log_type
		checkin.attendance_correction_request = self.name
		checkin.flags.ignore_permissions = True
		checkin.save()
		return checkin.name

	def recalculate_attendance_for_request(self) -> str | None:
		from hrms.hr.doctype.employee_checkin.employee_checkin_utils import recalculate_attendance

		attendance_date = str(getdate(self.attendance_date))
		previous_mute_messages = frappe.flags.mute_messages
		frappe.flags.mute_messages = True
		try:
			result = recalculate_attendance(
				self.employee,
				attendance_date,
				commit=False,
				ignore_permissions=True,
			)
		finally:
			frappe.flags.mute_messages = previous_mute_messages

		if result.get("status") == "success":
			return result.get("attendance")
		if result.get("status") in {"warning", "error"}:
			frappe.throw(result.get("message"))
		return None


def get_attendance_correction_approver(employee: str) -> str:
	approvers = get_attendance_correction_approvers(employee)
	if approvers:
		return approvers[0]

	frappe.throw(_("Attendance Correction Approver is not configured for employee {0}.").format(employee))


def get_attendance_correction_approvers(employee: str) -> list[str]:
	employee_values = frappe.db.get_value(
		"Employee",
		employee,
		["attendance_correction_approver", "department"],
	)
	if not employee_values or isinstance(employee_values, str):
		return []

	employee_approver, department = employee_values
	if employee_approver:
		return [employee_approver]

	if department:
		return [
			row.approver
			for row in frappe.get_all(
				"Department Approver",
				filters={
					"parent": department,
					"parentfield": "attendance_correction_approver",
				},
				fields=["approver"],
				order_by="idx asc",
			)
			if row.approver
		]

	return []


def is_attendance_correction_approver(employee: str, user: str) -> bool:
	return bool(user and user in get_attendance_correction_approvers(employee))


def user_can_manage_all_attendance_corrections(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = frappe.get_roles(user)
	return "System Manager" in roles or ATTENDANCE_CORRECTION_MANAGER_ROLE in roles
