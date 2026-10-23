# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

import frappe

from hrms.utils.attendance_qr import build_qr_payload

no_cache = 1


def generate_token_for_display(location_name: str) -> dict:
	"""
	为展示页面生成 token（服务端直接调用，无需认证）
	"""
	if not frappe.db.exists("QR Checkin Location", location_name):
		frappe.throw(f"打卡地点 {location_name} 不存在")

	doc = frappe.get_doc("QR Checkin Location", location_name)

	if not doc.enabled:
		frappe.throw(f"打卡地点 {location_name} 已禁用")

	return build_qr_payload(doc)


def get_context(context):
	"""
	为二维码展示页面提供上下文
	支持两种模式:
	1. 列表模式: /qr_display -> 显示所有启用的地点
	2. 展示模式: /qr_display?location=office-10F -> 显示特定二维码
	"""
	location_name = frappe.form_dict.get("location")

	if location_name:
		from hrms.hr.doctype.qr_checkin_location.qr_checkin_location import verify_display_key

		if frappe.db.exists("QR Checkin Location", location_name) and not verify_display_key(
			location_name, frappe.form_dict.get("key")
		):
			raise frappe.PermissionError

		# 展示模式: 显示特定地点的二维码
		# 直接生成初始 token
		token_data = generate_token_for_display(location_name)

		if isinstance(context, dict):
			context["location_name"] = token_data["location"]
			context["description"] = token_data["description"]
			context["initial_token"] = token_data["token"]
			context["refresh_interval"] = token_data["expires_in"]
		else:
			context.location_name = token_data["location"]
			context.description = token_data["description"]
			context.initial_token = token_data["token"]
			context.refresh_interval = token_data["expires_in"]
	else:
		# 列表模式: 显示所有启用的地点（只给 HR 和系统管理员看）
		if not set(frappe.get_roles()).intersection({"System Manager", "HR Manager", "HR User"}):
			raise frappe.PermissionError
		locations = frappe.get_all(
			"QR Checkin Location",
			filters={"enabled": 1},
			fields=["location_name", "description"],
			order_by="creation desc",
		)

		if isinstance(context, dict):
			context["locations"] = locations
		else:
			context.locations = locations

	return context
