# -*- coding: utf-8 -*-
# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

"""
动态二维码打卡 API
完全对接 hrms.hr.doctype.employee_checkin 的标准流程
"""

import time
import hmac
import hashlib
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now, now_datetime, get_datetime
from hrms.hr.utils import get_distance_between_coordinates

TIME_SLOT_SECONDS = 30  # 二维码时间片,与前端保持一致


def validate_ip_whitelist():
	"""
	验证请求 IP 是否在白名单中
	如果启用了 IP 限制，则检查当前请求 IP 是否在允许列表中
	"""
	try:
		hr_settings = frappe.get_single("HR Settings")
		
		# 如果启用了 IP 限制
		if hr_settings.get("qr_checkin_ip_restriction"):
			allowed_ips = hr_settings.get("qr_checkin_allowed_ips", "")
			if not allowed_ips:
				# 如果启用了限制但没有配置IP，允许所有（避免误配置导致无法打卡）
				return
			
			# 解析IP列表（支持换行分隔）
			allowed_ips_list = [ip.strip() for ip in allowed_ips.split("\n") if ip.strip()]
			
			if allowed_ips_list:
				# 获取客户端IP
				client_ip = frappe.local.request_ip or frappe.local.request.remote_addr
				
				# 检查IP是否在白名单中（支持CIDR格式，但这里简化处理，只做精确匹配）
				if client_ip not in allowed_ips_list:
					frappe.throw(
						_("Your network IP ({0}) is not in the allowed check-in range. Please contact HR.").format(client_ip),
						exc=frappe.exceptions.SecurityException
					)
	except Exception as e:
		# 如果获取设置失败，记录错误但不阻止打卡（避免配置错误导致系统不可用）
		frappe.log_error(
			message=f"IP whitelist validation error: {str(e)}",
			title="QR Checkin IP Validation Error"
		)


def _get_time_slot(ts=None):
	"""获取当前时间片编号"""
	if ts is None:
		ts = int(time.time())
	return ts // TIME_SLOT_SECONDS


def _sign(location_name: str, time_slot: int, secret: str) -> str:
	"""生成 HMAC-SHA256 签名"""
	msg = f"{location_name}|{time_slot}"
	return hmac.new(
		secret.encode("utf-8"),
		msg.encode("utf-8"),
		hashlib.sha256
	).hexdigest()[:8]  # 缩短到8字符以减小二维码大小


@frappe.whitelist(allow_guest=True)
def generate_qr_token(location_name: str):
	"""
	生成动态二维码 token
	供墙上展示页面调用（允许访客访问）
	
	Args:
		location_name: 地点名称
	
	Returns:
		{
			"token": "location_name|time_slot|signature",
			"expires_in": 30,
			"location": "office-10F",
			"description": "10楼办公室打卡点"
		}
	"""
	# 验证地点是否存在且启用
	if not frappe.db.exists("QR Checkin Location", location_name):
		frappe.throw(_("Check-in location {0} does not exist").format(location_name))
	
	doc = frappe.get_doc("QR Checkin Location", location_name)
	
	if not doc.enabled:
		frappe.throw(_("Check-in location {0} is disabled").format(location_name))
	
	time_slot = _get_time_slot()
	sig = _sign(doc.name, time_slot, doc.get_password("secret"))
	token = f"{doc.name}|{time_slot}|{sig}"
	
	return {
		"token": token,
		"expires_in": doc.qr_refresh_interval or TIME_SLOT_SECONDS,
		"location": doc.name,
		"description": doc.description
	}


@frappe.whitelist(allow_guest=False)
def qr_checkin(token: str, log_type: str = "IN", latitude: float = None, longitude: float = None):
	"""
	扫码打卡接口（支持地理位置验证）
	
	完全对接 hrms.hr.doctype.employee_checkin.employee_checkin 的标准流程
	复用现有的 Employee Checkin 验证和自动考勤逻辑
	
	Args:
		token: 二维码内容 "location_name|time_slot|signature"
		log_type: "IN" 或 "OUT"
		latitude: 纬度（可选，如果启用了地理位置追踪则必需）
		longitude: 经度（可选，如果启用了地理位置追踪则必需）
	
	Returns:
		{
			"status": "ok",
			"message": "签到成功",
			"checkin_name": "EMP-CKIN-...",
			"employee": "HR-EMP-00001",
			"employee_name": "张三",
			"time": "2025-11-19 17:30:00",
			"location": "office-10F"
		}
	"""
	# 1. 验证用户登录
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		frappe.throw(_("Please login before checking in"))
	
	# 1.5. IP白名单验证（如果启用）
	validate_ip_whitelist()
	
	# 2. 解析 token
	try:
		parts = token.split("|")
		if len(parts) != 3:
			raise ValueError("Invalid token format")
		location_name, time_slot_str, sig = parts
		time_slot = int(time_slot_str)
	except Exception:
		frappe.throw(_("Invalid QR code format, please scan again"))
	
	# 3. 验证地点配置
	if not frappe.db.exists("QR Checkin Location", location_name):
		frappe.throw(_("Check-in location does not exist"))
	
	doc = frappe.get_doc("QR Checkin Location", location_name)
	if not doc.enabled:
		frappe.throw(_("Check-in location is disabled"))
	
	secret = doc.get_password("secret")
	
	# 4. 验证签名和时效(允许当前和前一个时间片)
	valid = False
	current_slot = _get_time_slot()
	
	# 允许当前时间片和前一个时间片(共60秒有效期)
	# delta=0: 当前30秒, delta=-1: 前30秒
	for delta in (0, -1):
		expected_sig = _sign(location_name, current_slot + delta, secret)
		if hmac.compare_digest(expected_sig, sig):
			valid = True
			# 如果是前一个时间片，提示即将过期
			if delta == -1:
				frappe.msgprint(_("QR code is about to expire, please check in soon"), indicator="orange")
			break
	
	if not valid:
		frappe.throw(_("QR code has expired or is invalid, please scan again"))
	
	# 5. 获取当前员工
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		frappe.throw(_("Your account is not linked to an employee profile, please contact HR"))
	
	# 6. 防重复打卡检查(5分钟内不能重复相同类型的打卡)
	recent_checkin = frappe.db.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"log_type": log_type,
			"time": (">", now_datetime() - timedelta(minutes=5))
		},
		limit=1
	)
	
	if recent_checkin:
		action = _("checked in") if log_type == "IN" else _("checked out")
		frappe.throw(_("You have already {0} within the last 5 minutes, please do not check in repeatedly").format(action))
	
	# 7. 地理位置验证（如果启用了地理位置追踪）
	allow_geolocation_tracking = frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")
	
	if allow_geolocation_tracking:
		# 如果启用了地理位置追踪，必须提供经纬度
		if latitude is None or longitude is None:
			frappe.throw(_("Geolocation tracking is enabled. Please allow location access and try again."))
		
		# 如果 QR Checkin Location 关联了 Shift Location，验证距离
		if doc.shift_location:
			shift_location = frappe.get_doc("Shift Location", doc.shift_location)
			
			# 如果 Shift Location 配置了打卡半径，进行验证
			if shift_location.checkin_radius and shift_location.checkin_radius > 0:
				if not shift_location.latitude or not shift_location.longitude:
					frappe.throw(_("Shift Location {0} does not have valid coordinates configured").format(shift_location.name))
				
				distance = get_distance_between_coordinates(
					shift_location.latitude,
					shift_location.longitude,
					latitude,
					longitude
				)
				
				if distance > shift_location.checkin_radius:
					frappe.throw(
						_("You must be within {0} meters of the check-in location. Current distance: {1:.0f} meters").format(
							shift_location.checkin_radius,
							distance
						)
					)
	
	# 8. 创建 Employee Checkin (复用标准流程)
	# 注意: 这里直接调用标准 DocType,会自动触发:
	#   - validate_active_employee
	#   - validate_duplicate_log
	#   - fetch_shift (自动关联班次)
	#   - validate_distance_from_shift_location (如果启用了地理位置追踪)
	#   - 后续的自动考勤逻辑
	
	checkin_data = {
		"doctype": "Employee Checkin",
		"employee": employee,
		"time": now(),
		"log_type": log_type,
		"device_id": location_name,  # 记录打卡地点
		"skip_auto_attendance": 0,  # 不跳过自动考勤
	}
	
	# 如果提供了地理位置，设置经纬度
	if latitude is not None and longitude is not None:
		checkin_data["latitude"] = latitude
		checkin_data["longitude"] = longitude
	
	checkin = frappe.get_doc(checkin_data)
	
	try:
		checkin.insert(ignore_permissions=True)
		frappe.db.commit()
	except frappe.exceptions.ValidationError as e:
		# 捕获验证错误(如重复打卡、员工不活跃、地理位置超出范围等)
		frappe.throw(str(e))
	
	# 9. 记录审计日志
	try:
		client_ip = frappe.local.request_ip or frappe.local.request.remote_addr or "Unknown"
		geo_info = ""
		if latitude is not None and longitude is not None:
			geo_info = f" (Lat: {latitude:.5f}, Lng: {longitude:.5f})"
		
		# 使用 frappe.logger 记录审计日志（信息级别，不是错误）
		frappe.logger().info(
			f"QR Checkin Audit: Employee {employee} ({checkin.employee_name}) {log_type} at {location_name} on {checkin.time}. IP: {client_ip}{geo_info}"
		)
		
		# 同时使用 frappe.log_error 记录到错误日志表（便于查询和审计）
		# 使用特殊的title格式，便于区分审计日志和错误日志
		frappe.log_error(
			message=f"QR Checkin Audit: Employee {employee} ({checkin.employee_name}) {log_type} at {location_name} on {checkin.time}. IP: {client_ip}{geo_info}",
			title=f"QR Checkin Audit - {log_type}"
		)
	except Exception as log_error:
		# 日志记录失败不应影响打卡流程
		frappe.log_error(
			message=f"Failed to log QR checkin audit: {str(log_error)}",
			title="QR Checkin Audit Log Error"
		)
	
	# 10. 发送实时通知到二维码展示页面（公共房间，无需登录）
	try:
		action_text_ja = "出勤" if log_type == "IN" else "退勤"
		
		# 获取员工头像
		employee_image = frappe.db.get_value("Employee", employee, "image")
		
		# 发送到基于location的公共房间，所有访问该location二维码页面的人都能收到
		frappe.publish_realtime(
			event="qr_checkin_notification",
			message={
				"employee_name": checkin.employee_name,
				"employee_image": employee_image,
				"log_type": log_type,
				"action_ja": action_text_ja,
				"location": location_name,
				"time": str(checkin.time),
				"message_ja": f"{checkin.employee_name}さんが{action_text_ja}しました。お疲れ様です！"
			},
			room=f"qr_location_{location_name}",  # 基于location的房间
			after_commit=True  # 在事务提交后发送
		)
	except Exception as notify_error:
		# 通知发送失败不应影响打卡流程
		frappe.log_error(
			message=f"Failed to send QR checkin notification: {str(notify_error)}",
			title="QR Checkin Notification Error"
		)
	
	action = _("Check-in") if log_type == "IN" else _("Check-out")
	return {
		"status": "ok",
		"message": _("{0} successful").format(action),
		"checkin_name": checkin.name,
		"employee": employee,
		"employee_name": checkin.employee_name,
		"time": checkin.time,
		"location": location_name
	}


@frappe.whitelist(allow_guest=False)
def get_checkin_locations():
	"""
	获取所有启用的打卡地点列表
	供管理页面使用
	
	Returns:
		[
			{
				"name": "office-10F",
				"location_name": "office-10F",
				"description": "10楼办公室打卡点",
				"qr_refresh_interval": 30
			}
		]
	"""
	locations = frappe.get_all(
		"QR Checkin Location",
		filters={"enabled": 1},
		fields=["name", "location_name", "description", "qr_refresh_interval"],
		order_by="creation desc"
	)
	
	return locations


@frappe.whitelist(allow_guest=True)
def get_recent_checkins(location: str = None, limit: int = 5):
	"""
	获取最近的打卡记录（允许访客访问，用于二维码展示页面）
	
	Args:
		location: 打卡地点名称（可选）
		limit: 返回记录数（默认5条）
	
	Returns:
		[
			{
				"employee_name": "张三",
				"employee_image": "/files/employee.jpg",
				"log_type": "IN",
				"time": "2025-01-20 09:00:00",
				"location": "office-10F"
			}
		]
	"""
	filters = {}
	if location:
		filters["device_id"] = location
	
	checkins = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["employee_name", "employee", "log_type", "time", "device_id"],
		order_by="time desc",
		limit=limit
	)
	
	# 获取员工头像
	for checkin in checkins:
		if checkin.get("employee"):
			employee_image = frappe.db.get_value("Employee", checkin["employee"], "image")
			checkin["employee_image"] = employee_image
	
	return checkins

