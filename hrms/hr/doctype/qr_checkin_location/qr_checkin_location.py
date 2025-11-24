# -*- coding: utf-8 -*-
# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


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

