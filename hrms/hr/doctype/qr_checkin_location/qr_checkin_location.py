# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

import hmac
import secrets
from urllib.parse import urlencode

import frappe
from frappe.model.document import Document
from frappe.utils import cint, get_url
from frappe.utils.password import get_decrypted_password

DISPLAY_URL_ROLES = ("System Manager", "HR Manager")


class QRCheckinLocation(Document):
	def validate(self):
		"""验证打卡地点配置"""
		# 确保密钥不为空
		if not self.secret:
			frappe.throw("密钥不能为空，请设置一个强随机字符串")

		# 确保刷新间隔合理
		if self.qr_refresh_interval and self.qr_refresh_interval < 10:
			frappe.throw("二维码刷新间隔不能小于 10 秒")

		if self.qr_refresh_interval and self.qr_refresh_interval > 300:
			frappe.throw("二维码刷新间隔不能大于 300 秒")

		# 墙上屏展示密钥：首次保存时生成
		if not self.display_key:
			self.display_key = secrets.token_urlsafe(24)


def verify_display_key(location_name: str, key: str | None) -> bool:
	"""打卡点要求展示密钥时，只有带正确密钥的墙上屏能取码。"""
	if not cint(frappe.db.get_value("QR Checkin Location", location_name, "require_display_key")):
		return True
	expected = get_decrypted_password(
		"QR Checkin Location", location_name, "display_key", raise_exception=False
	)
	return bool(expected and key) and hmac.compare_digest(str(expected), str(key))


@frappe.whitelist()
def get_display_url(location_name: str) -> str:
	frappe.only_for(DISPLAY_URL_ROLES)
	doc = frappe.get_doc("QR Checkin Location", location_name)
	key = doc.get_password("display_key", raise_exception=False)
	return get_url("/qr_display?" + urlencode({"location": doc.name, "key": key or ""}))
