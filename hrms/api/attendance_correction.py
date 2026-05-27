import json

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate

import hrms
from hrms.hr.doctype.employee_checkin.employee_checkin_utils import get_attendance_recalculation_window
from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
	ATTENDANCE_CORRECTION_MANAGER_ROLE,
	get_attendance_correction_approvers,
	is_attendance_correction_approver,
	user_can_manage_all_attendance_corrections,
)

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
ATTENDANCE_CORRECTION_DETAIL_FIELDS = [
	*ATTENDANCE_CORRECTION_FIELDS,
	"original_checkin",
	"reason",
	"rejection_reason",
	"created_checkin",
	"updated_checkin",
	"result_attendance",
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
	return build_attendance_correction_context(employee, attendance_date)


def build_attendance_correction_context(employee: str, attendance_date) -> dict:
	attendance_date = getdate(attendance_date)
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
	if user_can_manage_all_attendance_corrections(frappe.session.user):
		return

	current_employee = _get_current_employee_for_user(frappe.session.user)
	if employee == current_employee:
		return

	if is_attendance_correction_approver(employee, frappe.session.user):
		return

	frappe.throw(_("You are not allowed to view this employee's attendance context."), frappe.PermissionError)


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

	for recipient in _get_attendance_correction_approval_resource_recipients(doc, approver):
		hrms.refetch_resource("hrms:pending_attendance_correction_approvals", recipient)
		hrms.refetch_resource("hrms:attendance_correction_approval_count", recipient)


def _get_attendance_correction_approval_resource_recipients(doc, approver: str | None = None) -> list[str]:
	recipients = []

	def add_recipient(user: str | None):
		if user and user not in recipients:
			recipients.append(user)

	add_recipient(approver)
	if getattr(doc, "employee", None):
		for user in get_attendance_correction_approvers(doc.employee):
			add_recipient(user)
	for user in _get_global_attendance_correction_manager_users():
		add_recipient(user)
	return recipients


def _get_global_attendance_correction_manager_users() -> list[str]:
	return [
		row.parent
		for row in frappe.get_all(
			"Has Role",
			filters={
				"parenttype": "User",
				"role": ["in", [ATTENDANCE_CORRECTION_MANAGER_ROLE, "System Manager"]],
			},
			fields=["parent"],
		)
		if row.parent
	]


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
	return _get_pending_attendance_correction_approvals(fields, _normalize_limit(limit))


@frappe.whitelist()
def get_attendance_correction_request(name: str) -> dict:
	doc = frappe.get_doc("Attendance Correction Request", name)
	validate_attendance_correction_request_access(doc)
	detail = {field: doc.get(field) for field in ATTENDANCE_CORRECTION_DETAIL_FIELDS}
	current_employee = _get_current_employee_for_user(frappe.session.user)
	detail["is_own_request"] = doc.employee == current_employee
	detail["can_approve"] = doc.status == "Pending" and can_user_approve_attendance_correction_request(
		doc.employee, frappe.session.user, doc.approver
	)
	detail["context"] = build_attendance_correction_context(doc.employee, doc.attendance_date)
	return detail


def validate_attendance_correction_request_access(doc):
	current_employee = _get_current_employee_for_user(frappe.session.user)
	if doc.employee == current_employee:
		return

	if can_user_approve_attendance_correction_request(doc.employee, frappe.session.user, doc.approver):
		return

	frappe.throw(_("You are not allowed to view this attendance correction request."), frappe.PermissionError)


@frappe.whitelist()
def get_attendance_correction_approval_count() -> int:
	if frappe.session.user == "Guest":
		return 0

	rows = _get_pending_attendance_correction_approvals(["count(distinct acr.name) as pending_count"])
	return rows[0].pending_count if rows else 0


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


def can_user_approve_attendance_correction_request(
	employee: str, user: str, assigned_approver: str | None = None
) -> bool:
	if assigned_approver and user == assigned_approver:
		return True
	return user_can_manage_all_attendance_corrections(user) or is_attendance_correction_approver(employee, user)


def _get_pending_attendance_correction_approvals(
	fields: list[str], limit: int | None = None
) -> list[dict]:
	user = frappe.session.user
	current_employee = _get_current_employee_for_user(user)
	is_count_query = fields == ["count(distinct acr.name) as pending_count"]
	conditions = ["acr.status = 'Pending'"]
	params = {"user": user}

	if not user_can_manage_all_attendance_corrections(user):
		conditions.append(
			"""
			(
				acr.approver = %(user)s
				or employee.attendance_correction_approver = %(user)s
				or (
					coalesce(employee.attendance_correction_approver, '') = ''
					and department_approver.name is not null
				)
			)
			"""
		)

	if current_employee:
		conditions.append("acr.employee != %(current_employee)s")
		params["current_employee"] = current_employee

	select_fields = ", ".join(_get_pending_approval_select_field(field) for field in fields)
	distinct_clause = "" if is_count_query else "distinct "
	order_clause = "" if is_count_query else "order by acr.creation desc"
	limit_clause = "limit %(limit)s" if limit and not is_count_query else ""
	if limit:
		params["limit"] = limit

	return frappe.db.sql(
		f"""
		select {distinct_clause}{select_fields}
		from `tabAttendance Correction Request` acr
		left join `tabEmployee` employee
			on employee.name = acr.employee
		left join `tabDepartment Approver` department_approver
			on department_approver.parent = employee.department
			and department_approver.parentfield = 'attendance_correction_approver'
			and department_approver.approver = %(user)s
		where {" and ".join(conditions)}
		{order_clause}
		{limit_clause}
		""",
		params,
		as_dict=True,
	)


def _get_pending_approval_select_field(field: str) -> str:
	if field == "count(distinct acr.name) as pending_count":
		return field
	return f"acr.`{field}`"


def _get_current_employee_for_user(user: str) -> str | None:
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		"name",
	)


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
