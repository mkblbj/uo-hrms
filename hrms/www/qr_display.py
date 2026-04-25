# -*- coding: utf-8 -*-
# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

import frappe
import time
import hmac
import hashlib

# 允许访客访问此页面（无需登录）
no_cache = 1

TIME_SLOT_SECONDS = 30


def _get_time_slot(ts=None):
	"""获取当前时间片编号"""
	if ts is None:
		ts = int(time.time())
	return ts // TIME_SLOT_SECONDS


def _sign(location_name: str, time_slot: int, secret: str) -> str:
	"""生成 HMAC-SHA256 签名（缩短到8字符以减小二维码大小）"""
	msg = f"{location_name}|{time_slot}"
	return hmac.new(
		secret.encode("utf-8"),
		msg.encode("utf-8"),
		hashlib.sha256
	).hexdigest()[:8]  # 缩短到8字符，仍有足够安全性


def generate_token_for_display(location_name: str) -> dict:
	"""
	为展示页面生成 token（服务端直接调用，无需认证）
	"""
	if not frappe.db.exists("QR Checkin Location", location_name):
		frappe.throw(f"打卡地点 {location_name} 不存在")
	
	doc = frappe.get_doc("QR Checkin Location", location_name)
	
	if not doc.enabled:
		frappe.throw(f"打卡地点 {location_name} 已禁用")
	
	time_slot = _get_time_slot()
	sig = _sign(doc.name, time_slot, doc.get_password("secret"))
	token = f"{doc.name}|{time_slot}|{sig}"
	
	return {
		"token": token,
		"expires_in": doc.qr_refresh_interval or TIME_SLOT_SECONDS,
		"location": doc.name,
		"description": doc.description
	}


def get_context(context):
	"""
	为二维码展示页面提供上下文
	支持两种模式:
	1. 列表模式: /qr_display -> 显示所有启用的地点
	2. 展示模式: /qr_display?location=office-10F -> 显示特定二维码
	"""
	location_name = frappe.form_dict.get("location")
	
	if location_name:
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
		# 列表模式: 显示所有启用的地点
		locations = frappe.get_all(
			"QR Checkin Location",
			filters={"enabled": 1},
			fields=["location_name", "description"],
			order_by="creation desc"
		)
		
		if isinstance(context, dict):
			context["locations"] = locations
		else:
			context.locations = locations
	
	return context

