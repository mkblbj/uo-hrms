import frappe


def has_stored_ble_key(name: str) -> bool:
	"""__Auth 里是否已有 ble_key 的密文（不管解不解得开）。"""
	auth = frappe.qb.DocType("__Auth")
	rows = (
		frappe.qb.from_(auth)
		.select(auth.name)
		.where(
			(auth.doctype == "QR Checkin Location")
			& (auth.name == name)
			& (auth.fieldname == "ble_key")
			& (auth.encrypted == 1)
			& (auth.password != "")
		)
		.limit(1)
		.run()
	)
	return bool(rows)


def execute():
	"""给现有打卡点生成签到牌蓝牙密钥（已有的不动）。"""
	for name in frappe.get_all("QR Checkin Location", pluck="name"):
		doc = frappe.get_doc("QR Checkin Location", name)
		if doc.get_password("ble_key", raise_exception=False):
			continue
		if has_stored_ble_key(name):
			# 有密文却解不开（如站点换了加密密钥）：不覆盖，免得旧密钥永远丢失；只提示地点名
			print(f"QR Checkin Location {name}: ble_key 已存在但无法解密，保持不变")
			continue
		# 列里可能还留着星号占位：不清掉的话 validate 不会重新生成，保存也会跳过占位值
		doc.ble_key = None
		doc.save(ignore_permissions=True)
