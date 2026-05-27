import frappe
from frappe.permissions import add_permission, update_permission_property

from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
	ATTENDANCE_CORRECTION_MANAGER_ROLE,
)
from hrms.patches.v16_0.add_attendance_correction_manager_role import execute as add_manager_role


ROLE_PERMISSIONS = {
	"Attendance": ("read", "create", "write", "submit", "cancel"),
	"Employee Checkin": ("read", "create", "write"),
	"Attendance Correction Request": ("read", "write"),
}


def execute():
	add_manager_role()

	for doctype, permissions in ROLE_PERMISSIONS.items():
		if not frappe.db.exists(
			"Custom DocPerm",
			{
				"parent": doctype,
				"role": ATTENDANCE_CORRECTION_MANAGER_ROLE,
				"permlevel": 0,
				"if_owner": 0,
			},
		):
			add_permission(doctype, ATTENDANCE_CORRECTION_MANAGER_ROLE, 0, permissions[0])

		for permission in permissions:
			update_permission_property(
				doctype,
				ATTENDANCE_CORRECTION_MANAGER_ROLE,
				0,
				permission,
				1,
				validate=False,
			)
		frappe.clear_cache(doctype=doctype)
