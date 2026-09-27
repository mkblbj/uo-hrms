import frappe


def execute():
	"""给现有打卡点生成展示密钥（默认不要求，墙上屏不受影响）。"""
	for name in frappe.get_all("QR Checkin Location", pluck="name"):
		doc = frappe.get_doc("QR Checkin Location", name)
		if not doc.get_password("display_key", raise_exception=False):
			doc.save(ignore_permissions=True)
