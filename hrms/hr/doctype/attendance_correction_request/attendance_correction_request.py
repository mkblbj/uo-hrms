import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate

from hrms.hr.utils import validate_active_employee


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
		self.validate_status_transition()
		self.validate_requested_time()
		self.validate_original_checkin()

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

		requested_date = getdate(self.requested_time)
		next_date = getdate(add_days(self.attendance_date, 1))
		if requested_date not in {self.attendance_date, next_date}:
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
