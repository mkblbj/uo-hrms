import frappe


def execute():
	"""给现有打卡点生成签到牌蓝牙密钥（已有的不动）。"""
	for name in frappe.get_all("QR Checkin Location", pluck="name"):
		doc = frappe.get_doc("QR Checkin Location", name)
		if not doc.get_password("ble_key", raise_exception=False):
			doc.save(ignore_permissions=True)
