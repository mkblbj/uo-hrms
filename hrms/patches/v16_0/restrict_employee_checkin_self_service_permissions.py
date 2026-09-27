import frappe
from frappe.permissions import setup_custom_perms, update_permission_property

SELF_SERVICE_ROLE = "Employee"


def execute():
	"""员工只能看自己的打卡记录，不能直接新建、修改、删除（打卡只走打卡接口）。"""
	setup_custom_perms("Employee Checkin")
	if not frappe.db.exists(
		"Custom DocPerm", {"parent": "Employee Checkin", "role": SELF_SERVICE_ROLE, "permlevel": 0}
	):
		return
	for ptype in ("write", "create", "delete"):
		update_permission_property("Employee Checkin", SELF_SERVICE_ROLE, 0, ptype, 0, validate=False)
	frappe.clear_cache(doctype="Employee Checkin")
