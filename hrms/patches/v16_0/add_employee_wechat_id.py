from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields


def execute():
	fields = [field for field in get_custom_fields()["Employee"] if field["fieldname"] == "custom_wechat_id"]
	create_custom_fields({"Employee": fields}, update=True)
