import frappe


def execute():
	"""给现有打卡点生成签到牌蓝牙密钥（已有的不动）。"""
	for name in frappe.get_all("QR Checkin Location", pluck="name"):
		doc = frappe.get_doc("QR Checkin Location", name)
		if not doc.get_password("ble_key", raise_exception=False):
			# 列里可能还留着星号占位：不清掉的话 validate 不会重新生成，保存也会跳过占位值
			doc.ble_key = None
			doc.save(ignore_permissions=True)
