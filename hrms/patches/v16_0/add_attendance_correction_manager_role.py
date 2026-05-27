import frappe

from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
	ATTENDANCE_CORRECTION_MANAGER_ROLE,
)


def execute():
	if frappe.db.exists("Role", ATTENDANCE_CORRECTION_MANAGER_ROLE):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": ATTENDANCE_CORRECTION_MANAGER_ROLE,
			"desk_access": 0,
			"is_custom": 0,
		}
	).insert(ignore_permissions=True)
