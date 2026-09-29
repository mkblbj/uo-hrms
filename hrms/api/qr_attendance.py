# Copyright (c) 2025, 株式会社UO and contributors
# For license information, please see license.txt

"""
动态二维码打卡 API
完全对接 hrms.hr.doctype.employee_checkin 的标准流程
"""

import hashlib
import hmac
import time

import frappe
from frappe import _
from frappe.utils import cint

from hrms.api.checkin_location import is_location_required
from hrms.api.checkin_presence import EVIDENCE_OFFICE_NETWORK, normalize_coordinates
from hrms.api.checkin_service import CHECKIN_METHOD_QR, create_checkin, validate_checkin_timing
from hrms.hr.doctype.qr_checkin_location.qr_checkin_location import verify_display_key
from hrms.hr.utils import get_distance_between_coordinates
from hrms.utils.client_network import get_client_ip, is_office_network, parse_network_list

TIME_SLOT_SECONDS = 30  # 二维码时间片,与前端保持一致
ATTENDANCE_STATUS_LABELS = {
	"working": "出勤中",
	"off_work": "退勤済",
	"not_checked_in": "未打刻",
}


def validate_ip_whitelist():
	"""开启 IP 限制且名单非空时，只允许公司网络打卡。读取设置出错时不挡人。"""
	try:
		settings = frappe.get_cached_doc("HR Settings")
		restriction_enabled = cint(settings.get("qr_checkin_ip_restriction"))
		networks_text = settings.get("qr_checkin_allowed_ips") or ""
	except Exception:
		frappe.log_error(title="QR Checkin IP Validation Error")
		return

	if not restriction_enabled or not parse_network_list(networks_text):
		return

	client_ip = get_client_ip()
	if not is_office_network(client_ip, networks_text):
		frappe.throw(
			_("Your network IP ({0}) is not in the allowed check-in range. Please contact HR.").format(
				client_ip
			),
			exc=frappe.exceptions.SecurityException,
		)


def _get_time_slot(ts=None):
	"""获取当前时间片编号"""
	if ts is None:
		ts = int(time.time())
	return ts // TIME_SLOT_SECONDS


def _sign(location_name: str, time_slot: int, secret: str) -> str:
	"""生成 HMAC-SHA256 签名"""
	msg = f"{location_name}|{time_slot}"
	return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()[
		:8
	]  # 缩短到8字符以减小二维码大小


@frappe.whitelist(allow_guest=True)
def generate_qr_token(location_name: str, key: str | None = None):
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

	if not verify_display_key(location_name, key):
		frappe.throw(_("Invalid display key"), frappe.PermissionError)

	doc = frappe.get_doc("QR Checkin Location", location_name)

	if not doc.enabled:
		frappe.throw(_("Check-in location {0} is disabled").format(location_name))

	server_time = int(time.time())
	time_slot = _get_time_slot(server_time)
	sig = _sign(doc.name, time_slot, doc.get_password("secret"))
	token = f"{doc.name}|{time_slot}|{sig}"
	frappe.local.response_headers.update(
		{
			"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
			"Pragma": "no-cache",
			"Expires": "0",
		}
	)

	return {
		"token": token,
		"expires_in": doc.qr_refresh_interval or TIME_SLOT_SECONDS,
		"location": doc.name,
		"description": doc.description,
		"server_time": server_time,
		"refresh_at": (time_slot + 1) * TIME_SLOT_SECONDS,
		"expires_at": (time_slot + 2) * TIME_SLOT_SECONDS,
	}


@frappe.whitelist(allow_guest=False)
def qr_checkin(
	token: str,
	log_type: str = "IN",
	latitude: float | None = None,
	longitude: float | None = None,
):
	"""
	扫码打卡接口（支持地理位置验证）

	完全对接 hrms.hr.doctype.employee_checkin.employee_checkin 的标准流程
	复用现有的 Employee Checkin 验证和自动考勤逻辑

	Args:
		token: 二维码内容 "location_name|time_slot|signature"
		log_type: "IN" 或 "OUT"
		latitude: 纬度（连着公司网络时不需要；否则开了地理位置追踪就必需）
		longitude: 经度（同上）

	Returns:
		缺定位时返回 {"status": "need_location"}，手机定位后再提交一次。
		成功时：
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
		_time_slot = int(time_slot_str)
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

	# 6-7. 冷却规则（与一键打卡共用）
	validate_checkin_timing(employee, log_type)

	# 8. 在场：连着公司网络就算在公司；否则开了地理位置追踪时要带定位，并按打卡点半径查距离
	client_ip = get_client_ip()
	on_office_network = is_office_network(client_ip)
	coordinates = normalize_coordinates(latitude, longitude)
	if is_location_required(on_office_network):
		if not coordinates:
			return {"status": "need_location"}
		_validate_distance_to_location(doc, coordinates)

	# 9-11. 建记录、审计、推送墙上屏
	latitude, longitude = coordinates or (None, None)
	checkin = create_checkin(
		employee=employee,
		log_type=log_type,
		location=location_name,
		method=CHECKIN_METHOD_QR,
		latitude=latitude,
		longitude=longitude,
		evidence=EVIDENCE_OFFICE_NETWORK if on_office_network else "qr",
		client_ip=client_ip,
	)

	action = _("Check-in") if log_type == "IN" else _("Check-out")
	return {
		"status": "ok",
		"message": _("{0} successful").format(action),
		"checkin_name": checkin.name,
		"employee": employee,
		"employee_name": checkin.employee_name,
		"time": checkin.time,
		"location": location_name,
	}


def _validate_distance_to_location(doc, coordinates: tuple[float, float]) -> None:
	"""打卡点关联了带半径的 Shift Location 时，定位必须在半径内。"""
	if not doc.shift_location:
		return
	shift_location = frappe.get_doc("Shift Location", doc.shift_location)
	if not shift_location.checkin_radius or shift_location.checkin_radius <= 0:
		return
	if not shift_location.latitude or not shift_location.longitude:
		frappe.throw(
			_("Shift Location {0} does not have valid coordinates configured").format(shift_location.name)
		)

	distance = get_distance_between_coordinates(
		shift_location.latitude, shift_location.longitude, coordinates[0], coordinates[1]
	)
	if distance > shift_location.checkin_radius:
		frappe.throw(
			_(
				"You must be within {0} meters of the check-in location. Current distance: {1:.0f} meters"
			).format(shift_location.checkin_radius, distance)
		)


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
		order_by="creation desc",
	)

	return locations


@frappe.whitelist(allow_guest=True)
def get_recent_checkins(location: str | None = None, limit: int = 5, compact: int = 0):
	"""
	获取最近的打卡记录（允许访客访问，用于二维码展示页面）

	Args:
		location: 打卡地点名称（可选）
		limit: 返回记录数（默认5条）
		compact: 轻量返回模式（1为启用）

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
	if compact == 1:
		if not location:
			frappe.throw(_("Location is required for compact check-ins"))

		limit = max(1, min(limit, 20))
		frappe.local.response_headers.update(
			{
				"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
				"Pragma": "no-cache",
				"Expires": "0",
			}
		)
		return frappe.get_all(
			"Employee Checkin",
			filters={"device_id": location},
			fields=["name", "log_type", "time", "device_id"],
			order_by="time desc, name desc",
			limit=limit,
		)

	filters = {}
	if location:
		filters["device_id"] = location

	checkins = frappe.get_all(
		"Employee Checkin",
		filters=filters,
		fields=["employee_name", "employee", "log_type", "time", "device_id"],
		order_by="time desc",
		limit=limit,
	)

	# 获取员工头像
	for checkin in checkins:
		if checkin.get("employee"):
			employee_image = frappe.db.get_value("Employee", checkin["employee"], "image")
			checkin["employee_image"] = employee_image

	return checkins


@frappe.whitelist(allow_guest=False)
def get_location_info(location_name: str):
	"""
	获取打卡地点信息（用于扫码确认页面显示）

	Args:
		location_name: 地点名称

	Returns:
		{
			"name": "office-10F",
			"description": "10楼办公室打卡点",
			"enabled": 1
		}
	"""
	if not frappe.db.exists("QR Checkin Location", location_name):
		return {"name": location_name, "description": location_name}

	doc = frappe.get_doc("QR Checkin Location", location_name)
	return {"name": doc.name, "description": doc.description or doc.name, "enabled": doc.enabled}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_employees_at_work(location: str | None = None):
	"""
	获取今天有打卡记录的员工列表，并标注当前状态

	最后一次打卡为 IN 时表示出勤中，最后一次打卡为 OUT 时表示退勤済。
	可用于其他应用调用，如当天出勤展示、门禁系统、会议室预约等。

	Args:
		location: 可选，筛选特定打卡地点的员工

	Returns:
		{
			"count": 5,
			"employees": [
				{
					"employee": "HR-EMP-00001",
					"employee_name": "山田太郎",
					"department": "技術部",
					"designation": "エンジニア",
					"image": "/files/employee.jpg",
					"checkin_time": "2025-12-01 09:00:00",
					"attendance_status": "working",
					"attendance_status_label": "出勤中",
					"last_log_type": "IN",
					"last_checkin_time": "09:00",
					"last_checkin_location": "office-10F",
					"location": "office-10F"
				},
				...
			]
		}

	API 调用示例:
		GET /api/method/hrms.api.qr_attendance.get_employees_at_work
		GET /api/method/hrms.api.qr_attendance.get_employees_at_work?location=office-10F
	"""
	today = frappe.utils.today()

	# 子查询：获取每个员工今天最后一次打卡记录
	# 使用 SQL 直接查询，效率更高
	sql = """
		SELECT
			ec.employee,
			ec.employee_name,
			ec.log_type,
			ec.time,
			ec.device_id as location,
			e.department,
			e.designation,
			e.image
		FROM `tabEmployee Checkin` ec
		INNER JOIN `tabEmployee` e ON e.name = ec.employee
		WHERE ec.time = (
			SELECT MAX(ec2.time)
			FROM `tabEmployee Checkin` ec2
			WHERE ec2.employee = ec.employee
			AND DATE(ec2.time) = %s
		)
		AND DATE(ec.time) = %s
		AND e.status = 'Active'
	"""

	params = [today, today]

	if location:
		sql += " AND ec.device_id = %s"
		params.append(location)

	sql += " ORDER BY ec.time DESC"

	results = frappe.db.sql(sql, params, as_dict=True)

	# 格式化返回数据
	employees = []
	for row in results:
		attendance_status = _get_attendance_status_from_log_type(row.log_type)
		checkin_time = _format_checkin_time(row.time, include_seconds=True)
		last_checkin_time = _format_checkin_time(row.time)
		employees.append(
			{
				"employee": row.employee,
				"employee_name": row.employee_name,
				"department": row.department,
				"designation": row.designation,
				"image": row.image,
				"checkin_time": checkin_time,
				"attendance_status": attendance_status,
				"attendance_status_label": ATTENDANCE_STATUS_LABELS[attendance_status],
				"last_log_type": row.log_type,
				"last_checkin_time": last_checkin_time,
				"last_checkin_location": row.location,
				"location": row.location,
			}
		)

	return {"count": len(employees), "employees": employees}


def _get_attendance_status_from_log_type(log_type):
	if log_type == "IN":
		return "working"
	if log_type == "OUT":
		return "off_work"
	return "not_checked_in"


def _format_checkin_time(value, include_seconds=False):
	text = str(value)
	time_part = text.split(" ")[-1]
	parts = time_part.split(":")
	if include_seconds and len(parts) >= 3:
		return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2]}"
	if len(parts) >= 2:
		return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
	return text
