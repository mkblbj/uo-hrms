"""原生 iOS App 专用接口（按 hrms.api.mobile.<fn> 调用）。

只做汇总：数据仍由现有接口和 hrms.utils.mobile_home 的规则算出，PWA 不受影响。
"""

import frappe
from frappe import _
from frappe.utils import cint, get_system_timezone, now_datetime

from hrms.api import get_current_user_info, get_unread_notifications_count
from hrms.api.passkey import _passkey_checkin_enabled_for, _passkey_checkin_location

API_VERSION = 1
_TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _require_login() -> str:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login first"), frappe.PermissionError)
	return user


def _active_employee(user: str) -> dict | None:
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "employee_name", "first_name", "department", "designation", "company", "reports_to"],
		as_dict=True,
	)


def _mobile_checkin_allowed() -> bool:
	# 和 PWA 的 Boolean(allow_employee_checkin_from_mobile_app) 一致
	return bool(cint(frappe.db.get_single_value("HR Settings", "allow_employee_checkin_from_mobile_app")))


def _profile_collection_enabled() -> bool:
	# employee_profile 在部分环境里还没进版本库，找不到就当作没开
	try:
		get_status = frappe.get_attr("hrms.api.employee_profile.get_collection_status")
	except (ImportError, AttributeError):
		return False
	try:
		return bool((get_status() or {}).get("enabled"))
	except frappe.PermissionError:
		return False


@frappe.whitelist(methods=["GET", "POST"])
def get_boot() -> dict:
	"""App 启动时取一次：当前用户、员工、功能开关、打卡地点、未读数。"""
	user = _require_login()
	user_info = get_current_user_info()
	employee = _active_employee(user)
	location = _passkey_checkin_location() if employee else None
	passkey_enabled = bool(location) and _passkey_checkin_enabled_for(employee.name)

	features = {
		"mobile_checkin": False,
		"passkey_checkin": False,
		"geolocation_required": False,
		"profile_collection": False,
	}
	if employee:
		features = {
			"mobile_checkin": _mobile_checkin_allowed(),
			"passkey_checkin": passkey_enabled,
			"geolocation_required": bool(
				cint(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking"))
			),
			"profile_collection": _profile_collection_enabled(),
		}

	return {
		"api_version": API_VERSION,
		"server_time": now_datetime().strftime(_TIME_FMT),
		"timezone": get_system_timezone(),
		"user": {
			"name": user_info.get("name"),
			"full_name": user_info.get("full_name"),
			"first_name": user_info.get("first_name"),
			"user_image": user_info.get("user_image"),
			"language": frappe.local.lang,
		},
		"employee": {
			"name": employee.name,
			"employee_name": employee.employee_name,
			"first_name": employee.first_name,
			"department": employee.department,
			"designation": employee.designation,
			"company": employee.company,
			"reports_to_name": frappe.db.get_value("Employee", employee.reports_to, "employee_name")
			if employee.reports_to
			else None,
		}
		if employee
		else None,
		"features": features,
		"checkin_location": {
			"name": location,
			"description": frappe.db.get_value("QR Checkin Location", location, "description") or location,
		}
		if passkey_enabled
		else None,
		"unread_notifications": cint(get_unread_notifications_count()),
	}
