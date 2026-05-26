import json

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

import hrms
from hrms.hr.doctype.employee_checkin.employee_checkin_utils import get_attendance_recalculation_window

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
ATTENDANCE_CORRECTION_FIELDS = [
	"name",
	"employee",
	"employee_name",
	"attendance_date",
	"request_type",
	"requested_log_type",
	"requested_time",
	"status",
	"approver",
	"creation",
]


@frappe.whitelist()
def get_current_employee() -> str:
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		"name",
	)
	if not employee:
		frappe.throw(_("Current user is not linked to an active employee."))
	return employee


@frappe.whitelist()
def get_attendance_correction_context(date: str, employee: str | None = None) -> dict:
	employee = employee or get_current_employee()
	validate_employee_context_access(employee)
	attendance_date = getdate(date)
	shift = get_employee_shift_for_date(employee, attendance_date)
	start_datetime, end_datetime = get_checkin_window(attendance_date, shift)

	return {
		"employee": employee,
		"attendance_date": str(attendance_date),
		"shift": shift,
		"checkins": frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": employee,
				"time": ["between", [start_datetime, end_datetime]],
			},
			fields=["name", "employee", "log_type", "time", "shift", "attendance"],
			order_by="time asc",
		),
		"attendance": frappe.db.get_value(
			"Attendance",
			{"employee": employee, "attendance_date": attendance_date, "docstatus": 1},
			["name", "status", "working_hours", "in_time", "out_time"],
			as_dict=True,
		),
	}


def validate_employee_context_access(employee: str):
	if frappe.session.user == "Administrator":
		return

	if "HR Manager" in frappe.get_roles() or "System Manager" in frappe.get_roles():
		return

	current_employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		"name",
	)
	if employee == current_employee:
		return

	if is_attendance_correction_approver(employee, frappe.session.user):
		return

	frappe.throw(_("You are not allowed to view this employee's attendance context."), frappe.PermissionError)


def is_attendance_correction_approver(employee: str, user: str) -> bool:
	employee_values = frappe.db.get_value(
		"Employee",
		employee,
		["attendance_correction_approver", "department"],
	)
	if not employee_values:
		return False

	employee_approver, department = employee_values
	if employee_approver:
		return employee_approver == user

	return bool(
		department
		and frappe.db.exists(
			"Department Approver",
			{
				"parent": department,
				"parentfield": "attendance_correction_approver",
				"approver": user,
				"idx": 1,
			},
		)
	)


def get_employee_shift_for_date(employee: str, attendance_date) -> str | None:
	shift_assignments = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"status": "Active",
			"start_date": ["<=", attendance_date],
			"docstatus": 1,
		},
		or_filters=[["end_date", ">=", attendance_date], ["end_date", "is", "not set"]],
		fields=["shift_type"],
		order_by="start_date desc",
		limit=1,
	)
	return shift_assignments[0].shift_type if shift_assignments else None


def get_checkin_window(attendance_date, shift: str | None):
	if not shift:
		return (
			get_datetime(f"{attendance_date} 00:00:00"),
			get_datetime(f"{attendance_date} 23:59:59"),
		)

	return get_attendance_recalculation_window(frappe.get_doc("Shift Type", shift), attendance_date)


@frappe.whitelist()
def submit_attendance_correction_request(payload: dict | str) -> dict:
	payload = _parse_payload(payload)
	employee = get_current_employee()
	doc = frappe.get_doc(
		{
			"doctype": "Attendance Correction Request",
			"employee": employee,
			"attendance_date": payload.get("attendance_date"),
			"request_type": payload.get("request_type"),
			"requested_log_type": payload.get("requested_log_type"),
			"requested_time": payload.get("requested_time"),
			"original_checkin": payload.get("original_checkin"),
			"reason": payload.get("reason"),
			"status": "Pending",
		}
	)
	doc.insert(ignore_permissions=True)

	_refetch_attendance_correction_resources(doc, doc.approver)

	return {"name": doc.name, "status": doc.status}


def _refetch_attendance_correction_resources(doc, approver: str | None = None):
	if getattr(doc, "owner", None):
		hrms.refetch_resource("hrms:my_attendance_correction_requests", doc.owner)
	if approver:
		hrms.refetch_resource("hrms:pending_attendance_correction_approvals", approver)
		hrms.refetch_resource("hrms:attendance_correction_approval_count", approver)


@frappe.whitelist()
def get_my_attendance_correction_requests(limit: int | None = 20) -> list[dict]:
	return frappe.get_list(
		"Attendance Correction Request",
		filters={"employee": get_current_employee()},
		fields=ATTENDANCE_CORRECTION_FIELDS,
		order_by="creation desc",
		limit_page_length=_normalize_limit(limit),
	)


@frappe.whitelist()
def get_pending_attendance_correction_approvals(limit: int | None = 20) -> list[dict]:
	fields = [*ATTENDANCE_CORRECTION_FIELDS, "reason"]
	fields.remove("approver")
	return frappe.get_all(
		"Attendance Correction Request",
		filters={"approver": frappe.session.user, "status": "Pending"},
		fields=fields,
		order_by="creation desc",
		limit_page_length=_normalize_limit(limit),
	)


@frappe.whitelist()
def get_attendance_correction_approval_count() -> int:
	if frappe.session.user in {"Guest", "Administrator"}:
		return 0

	return frappe.db.count(
		"Attendance Correction Request",
		{"approver": frappe.session.user, "status": "Pending"},
	)


@frappe.whitelist()
def approve_attendance_correction_request(name: str) -> dict:
	doc = frappe.get_doc("Attendance Correction Request", name)
	approver = doc.approver
	doc.approve(frappe.session.user)
	_refetch_attendance_correction_resources(doc, approver)
	return {"name": doc.name, "status": doc.status, "attendance": doc.result_attendance}


@frappe.whitelist()
def reject_attendance_correction_request(name: str, reason: str) -> dict:
	doc = frappe.get_doc("Attendance Correction Request", name)
	approver = doc.approver
	doc.reject(reason, frappe.session.user)
	_refetch_attendance_correction_resources(doc, approver)
	return {"name": doc.name, "status": doc.status}


def _parse_payload(payload: dict | str) -> dict:
	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except json.JSONDecodeError:
			frappe.throw(_("Invalid attendance correction request payload."))
	if not isinstance(payload, dict):
		frappe.throw(_("Invalid attendance correction request payload."))
	return payload


def _normalize_limit(limit: int | str | None) -> int:
	if limit is None:
		return DEFAULT_LIMIT

	try:
		limit = int(limit)
	except (TypeError, ValueError):
		frappe.throw(_("Limit must be a positive integer."))

	if limit < 1 or limit > MAX_LIMIT:
		frappe.throw(_("Limit must be between 1 and {0}.").format(MAX_LIMIT))

	return limit
