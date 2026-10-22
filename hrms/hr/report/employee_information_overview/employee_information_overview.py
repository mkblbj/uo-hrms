import frappe
from frappe import _
from frappe.utils import cint, cstr


def execute(filters=None):
	if not set(frappe.get_roles()) & {"HR User", "HR Manager", "System Manager"}:
		frappe.throw(
			_("Only HR users and administrators can view employee information."), frappe.PermissionError
		)

	filters = frappe._dict(filters or {})
	conditions = {key: filters[key] for key in ("company", "department", "status") if filters.get(key)}
	rows = frappe.get_list(
		"Employee",
		fields=[
			"name",
			"employee_number",
			"employee_name",
			"company",
			"department",
			"user_id",
			"status",
			"cell_number",
			"custom_wechat_id",
			"current_address",
			"person_to_be_contacted",
			"relation",
			"emergency_phone_number",
			"company_email",
			"personal_email",
			"date_of_joining",
		],
		filters=conditions,
		order_by="employee_name asc, name asc",
		limit_page_length=0,
	)
	search = cstr(filters.get("search")).strip().casefold()
	data = []
	for row in rows:
		if search and not any(
			search in cstr(row.get(field)).casefold()
			for field in ("name", "employee_number", "employee_name", "cell_number", "custom_wechat_id")
		):
			continue
		if cint(filters.get("missing_phone")) and cstr(row.get("cell_number")).strip():
			continue
		if cint(filters.get("missing_address")) and cstr(row.get("current_address")).strip():
			continue
		company_email = cstr(row.pop("company_email", None)).strip()
		personal_email = cstr(row.pop("personal_email", None)).strip()
		account_email = cstr(row.pop("user_id", None)).strip()
		row["contact_email"] = (
			company_email or personal_email or (account_email if "@" in account_email else "")
		)
		data.append(row)
	return get_columns(), data


def get_columns():
	return [
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 150,
			"sticky": True,
		},
		{
			"fieldname": "name",
			"label": _("Employee ID"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 160,
			"sticky": True,
		},
		{"fieldname": "employee_number", "label": _("Employee Number"), "fieldtype": "Data", "width": 130},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 100},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{"fieldname": "contact_email", "label": _("Email"), "fieldtype": "Data", "width": 220},
		{"fieldname": "cell_number", "label": _("Mobile"), "fieldtype": "Data", "width": 180},
		{"fieldname": "custom_wechat_id", "label": _("WeChat ID"), "fieldtype": "Data", "width": 170},
		{"fieldname": "current_address", "label": _("Current Address"), "fieldtype": "Data", "width": 300},
		{
			"fieldname": "person_to_be_contacted",
			"label": _("Emergency Contact Name"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "relation",
			"label": _("Emergency Contact Relationship"),
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"fieldname": "emergency_phone_number",
			"label": _("Emergency Phone"),
			"fieldtype": "Data",
			"width": 180,
		},
		{"fieldname": "date_of_joining", "label": _("Date of Joining"), "fieldtype": "Date", "width": 110},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
	]
