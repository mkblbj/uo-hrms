from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	custom_fields = {
		"Department": [
			{
				"fieldname": "attendance_correction_approver",
				"fieldtype": "Table",
				"label": _("Attendance Correction Approver"),
				"options": "Department Approver",
				"insert_after": "expense_approvers",
			}
		],
		"Employee": [
			{
				"fieldname": "attendance_correction_approver",
				"fieldtype": "Link",
				"label": _("Attendance Correction Approver"),
				"options": "User",
				"insert_after": "shift_request_approver",
				"ignore_user_permissions": 1,
			}
		],
	}
	create_custom_fields(custom_fields, ignore_validate=True)
