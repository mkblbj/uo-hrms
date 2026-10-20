"""原生 iOS App 专用接口（按 hrms.api.mobile.<fn> 调用）。

只做汇总：数据仍由现有接口和 hrms.utils.mobile_home 的规则算出，PWA 不受影响。
"""

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import (
	cint,
	flt,
	get_datetime,
	get_last_day,
	get_system_timezone,
	getdate,
	now_datetime,
	strip_html_tags,
)

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

from hrms.api import (
	get_attendance_calendar_events,
	get_attendance_day_details,
	get_current_user_info,
	get_employee_dashboard_stats,
	get_employee_work_status,
	get_unread_notifications_count,
	get_weather_data,
)
from hrms.api.checkin_location import get_location_requirement
from hrms.api.passkey import _passkey_checkin_enabled_for, _passkey_checkin_location, get_checkin_context
from hrms.api.profile_photo import get_profile_photo_status
from hrms.utils import mobile_attendance, mobile_home

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


WEATHER_CACHE_SECONDS = 600
WEATHER_FAILURE_CACHE_SECONDS = 300
_WEATHER_FAILED = {"_failed": True}


def _schedule_summary() -> dict:
	"""work_roster 的今日 / 下次班次、大促和排班希望；没装 work_roster 时为空。"""
	if "work_roster" not in frappe.get_installed_apps():
		return {}
	from work_roster.api.schedule import get_home_schedule_summary

	summary = get_home_schedule_summary() or {}
	return {} if summary.get("error") else summary


def _scheduled_days(today) -> int | None:
	"""本人本月已发布的排班天数。"""
	if "work_roster" not in frappe.get_installed_apps():
		return None
	from work_roster.api.schedule import get_my_schedule

	return len(get_my_schedule(month=today.month, year=today.year) or [])


def _shift(entry: dict | None) -> dict | None:
	if not entry:
		return None
	start = entry.get("start_time") or mobile_home._clock(entry.get("custom_start_time")) or None
	end = entry.get("end_time") or mobile_home._clock(entry.get("custom_end_time")) or None
	return {
		"date": entry.get("date"),
		"start_time": start,
		"end_time": end,
		"hours": flt(entry.get("hours")),
		"slot": entry.get("wr_shift_slot") or entry.get("shift_label"),
	}


def _weather() -> dict | None:
	key = f"mobile:weather:{frappe.local.lang}"
	data = frappe.cache.get_value(key)
	if data is None:
		try:
			data = get_weather_data()
		except Exception:
			data = None
		# 失败也记 5 分钟：天气服务挂掉时不让每次打开主页都等满超时
		frappe.cache.set_value(
			key,
			data or _WEATHER_FAILED,
			expires_in_sec=WEATHER_CACHE_SECONDS if data else WEATHER_FAILURE_CACHE_SECONDS,
		)
	if not data or data == _WEATHER_FAILED:
		return None
	condition = data.get("condition") or {}
	icon = condition.get("icon") or ""
	return {
		"temp_c": flt(data.get("temp_c")),
		"condition": condition.get("text"),
		"icon_url": f"https:{icon}" if icon.startswith("//") else icon or None,
		"max_c": data.get("maxtemp_c"),
		"min_c": data.get("mintemp_c"),
	}


def _profile_photo_reminder() -> dict:
	try:
		status = get_profile_photo_status() or {}
	except frappe.PermissionError:
		return {"show": False, "temporary": False}
	has_photo = bool(status.get("has_photo"))
	temporary = status.get("temporary")
	if temporary is None:
		temporary = bool(status.get("photo")) and not has_photo
	return {"show": bool(status.get("required")) and not has_photo, "temporary": bool(temporary)}


@frappe.whitelist(methods=["GET"])
def get_home_snapshot() -> dict:
	"""主页一次取齐：今日卡、热力图、本月统计、班次、希望提醒、天气、打卡入口、提醒卡。"""
	user = _require_login()
	employee = _active_employee(user)
	if not employee:
		frappe.throw(_("No active employee record found for your account"), frappe.PermissionError)

	now = now_datetime()
	today = now.date()
	work_status = get_employee_work_status() or {}
	stats = get_employee_dashboard_stats() or {}
	summary = _schedule_summary()

	first_day, last_day = mobile_home.heatmap_range(today)
	events = get_attendance_calendar_events(first_day.isoformat(), last_day.isoformat()) or {}
	cells = mobile_home.heatmap_cells(events, today)

	# month_half_days 已经按每个半天 0.5 天计
	present_days = flt(stats.get("month_present")) + flt(stats.get("month_half_days"))
	month_hours = flt(stats.get("month_hours"))
	event = summary.get("today_event")
	context = get_checkin_context()
	requirement = get_location_requirement()

	return {
		"api_version": API_VERSION,
		"today": today.isoformat(),
		"now": now.strftime(_TIME_FMT),
		"first_name": employee.first_name or employee.employee_name,
		"work_status": {
			"status": work_status.get("status") or "no_checkin_today",
			"last_checkin": work_status.get("last_checkin"),
			"first_checkin_today": stats.get("first_checkin_today"),
			"last_checkin_today": stats.get("last_checkin_today"),
		},
		"today_shift": _shift(summary.get("today_entry")),
		"next_shift": _shift(summary.get("next_entry")),
		"progress": mobile_home.today_progress(summary.get("today_entry"), stats, work_status, now),
		"sale_event": {k: event.get(k) for k in ("title", "event_type", "color")} if event else None,
		"heatmap": {
			"weeks": mobile_home.HEATMAP_WEEKS,
			"cells": cells,
			"month_markers": mobile_home.heatmap_month_markers(cells),
		},
		"month": {
			"hours": month_hours,
			"present_days": present_days,
			"scheduled_days": _scheduled_days(today),
			"average_hours": round(month_hours / present_days, 2) if present_days else 0,
		},
		"preference_notices": mobile_home.preference_notices(summary, today),
		"weather": _weather(),
		"checkin": {**context, "location_required": bool(requirement.get("location_required"))},
		"reminders": {
			"profile_photo": _profile_photo_reminder(),
			"passkey_setup": _mobile_checkin_allowed() and bool(context.get("enabled")) and not context.get("has_passkey"),
		},
	}


# ---- 勤怠（M2）----


def _require_employee() -> dict:
	employee = _active_employee(_require_login())
	if not employee:
		frappe.throw(_("No active employee record found for your account"), frappe.PermissionError)
	return employee


def _month_schedule(year: int, month: int) -> dict | None:
	"""work_roster 的本人月排班（已发布）和假日；没装 work_roster 时为 None。"""
	if "work_roster" not in frappe.get_installed_apps():
		return None
	from work_roster.api.schedule import get_my_schedule_calendar_data

	return get_my_schedule_calendar_data(month=month, year=year) or {}


def _roster_entry(employee: str, day: date) -> dict | None:
	"""某个员工某一天的已发布排班条目（work_roster 的格式）；没有时 None。"""
	if "work_roster" not in frappe.get_installed_apps():
		return None
	from work_roster.api import schedule as roster

	entries, period_map, slot_map = roster._get_published_schedule_entries_for_employee(employee, day.isoformat())
	entry = next((row for row in entries if str(row.date) == day.isoformat()), None)
	return roster._serialize_schedule_entry(entry, period_map, slot_map) if entry else None


def _holiday_map(employee: str, roster_holidays: list | None, first: date, last: date) -> dict[str, dict]:
	"""日期 → {description, weekly_off}：先放 hrms 员工假日表，再用排班模块的假日覆盖（PWA 月历用的就是后者）。"""
	holidays = {}
	if holiday_list := get_holiday_list_for_employee(employee, raise_exception=False):
		for row in frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [first, last]]},
			fields=["holiday_date", "description", "weekly_off"],
		):
			holidays[str(row.holiday_date)] = {"description": row.description, "weekly_off": cint(row.weekly_off)}
	for row in roster_holidays or []:
		holidays[str(row.get("holiday_date"))[:10]] = {
			"description": row.get("description"),
			"weekly_off": cint(row.get("weekly_off")),
		}
	return holidays


def _pending_correction_dates(employee: str, first: date, last: date) -> set[str]:
	return {
		str(day)
		for day in frappe.get_all(
			"Attendance Correction Request",
			filters={"employee": employee, "status": "Pending", "attendance_date": ["between", [first, last]]},
			pluck="attendance_date",
		)
	}


def _anomaly_codes(event: dict | None) -> list[str]:
	anomaly = (event or {}).get("anomaly") or {}
	return list(anomaly.get("codes") or []) if anomaly.get("has_issue") else []


def _holiday_name(holiday: dict | None) -> str | None:
	if not holiday or holiday.get("weekly_off"):
		return None
	return strip_html_tags(holiday.get("description") or "").strip() or None


@frappe.whitelist(methods=["GET"])
def get_attendance_month(year: int, month: int) -> dict:
	"""勤怠月历：这个月每一天的状态、工时，以及月度汇总。"""
	employee = _require_employee()
	year, month = cint(year), cint(month)
	if not 1 <= month <= 12 or not 2000 <= year <= 2100:
		frappe.throw(_("Invalid year or month"))

	first = date(year, month, 1)
	last = get_last_day(first)
	today = now_datetime().date()
	schedule = _month_schedule(year, month)
	roster_by_date = {str(entry.get("date"))[:10]: entry for entry in (schedule or {}).get("entries") or []}
	holidays = _holiday_map(employee.name, (schedule or {}).get("holidays"), first, last)
	events = get_attendance_calendar_events(first.isoformat(), last.isoformat()) or {}
	pending = _pending_correction_dates(employee.name, first, last)

	days = []
	for offset in range((last - first).days + 1):
		day = first + timedelta(days=offset)
		key = day.isoformat()
		event, holiday, entry = events.get(key), holidays.get(key), roster_by_date.get(key)
		hours = mobile_attendance.day_hours(event)
		days.append(
			{
				"date": key,
				"weekday": day.isoweekday(),
				"is_today": day == today,
				"is_future": day > today,
				"state": mobile_attendance.derive_day_state(event, holiday, entry, day, today),
				"hours": hours,
				"is_half_day": (event or {}).get("attendance") == "Half Day",
				"anomaly_codes": _anomaly_codes(event),
				"has_pending_correction": key in pending,
				"holiday_name": _holiday_name(holiday),
				"_weight": mobile_attendance.day_weight(event),
				"_leave": mobile_attendance.leave_weight(event),
				"_overtime": mobile_attendance.day_overtime(hours, (entry or {}).get("hours")),
			}
		)

	if schedule is None:
		scheduled_days = remaining_days = None
	else:
		scheduled_days = sum(1 for key in roster_by_date if first.isoformat() <= key <= last.isoformat())
		remaining_days = sum(1 for key in roster_by_date if today.isoformat() < key <= last.isoformat())
	summary = mobile_attendance.summarize_month(days, scheduled_days, remaining_days)
	for row in days:
		for key in ("_weight", "_leave", "_overtime"):
			del row[key]
	return {
		"api_version": API_VERSION,
		"year": year,
		"month": month,
		"today": today.isoformat(),
		"days": days,
		"summary": summary,
	}


def _sale_event(events: list | None, key: str) -> dict | None:
	"""同一天有多个时 Major Sale 优先（和 PWA 月历一致）。"""
	picked = None
	for event in events or []:
		if str(event.get("event_date"))[:10] != key:
			continue
		if picked is None or event.get("event_type") == "Major Sale":
			picked = event
	return {k: picked.get(k) for k in ("title", "event_type", "color")} if picked else None


def _lunch_window(employee: str, day: date) -> tuple:
	"""当天用于计算的 Shift Type 的午休（取法同 get_attendance_day_details）；没开午休扣除时为 (None, None)。"""
	from hrms.api.attendance_correction import get_employee_shift_for_date

	shift = (
		frappe.db.get_value("Attendance", {"employee": employee, "attendance_date": day, "docstatus": 1}, "shift")
		or get_employee_shift_for_date(employee, day)
		or frappe.db.get_value("Employee", employee, "default_shift")
	)
	values = shift and frappe.db.get_value(
		"Shift Type", shift, ["enable_lunch_deduction", "lunch_start", "lunch_end"], as_dict=True
	)
	if not values or not cint(values.enable_lunch_deduction):
		return None, None
	return values.lunch_start, values.lunch_end


def _punches(checkins: list[dict]) -> list[dict]:
	names = [row["name"] for row in checkins]
	extra = {
		row.name: row
		for row in frappe.get_all(
			"Employee Checkin",
			filters={"name": ["in", names or [""]]},
			fields=["name", "device_id", "latitude", "longitude"],
		)
	}
	device_ids = {row.device_id for row in extra.values() if row.device_id}
	locations = {
		row.name: strip_html_tags(row.description or "").strip() or row.name
		for row in frappe.get_all(
			"QR Checkin Location",
			filters={"name": ["in", list(device_ids) or [""]]},
			fields=["name", "description"],
		)
	}
	punches = []
	for row in checkins:
		info = extra.get(row["name"]) or frappe._dict()
		method = mobile_attendance.punch_method(row.get("checkin_method"))
		punches.append(
			{
				"time": get_datetime(row["time"]).strftime(_TIME_FMT),
				"log_type": row.get("log_type"),
				"method": method,
				"evidence": mobile_attendance.punch_evidence(method, info.latitude, info.longitude),
				"location_name": locations.get(info.device_id),
				"included": bool(row.get("included_in_calculation")),
			}
		)
	return punches


@frappe.whitelist(methods=["GET"])
def get_attendance_day(date: str) -> dict:
	"""勤怠日详情：班次、工时、计入的时段、午休和每条打卡。"""
	employee = _require_employee()
	day = getdate(date)
	key = day.isoformat()

	schedule = _month_schedule(day.year, day.month) or {}
	entry = next((row for row in schedule.get("entries") or [] if str(row.get("date"))[:10] == key), None)
	details = get_attendance_day_details(key)
	worked = details.get("working_hours") if details.get("is_settled") else None
	worked_hours = mobile_attendance.round1(worked if worked is not None else details.get("completed_hours") or 0)
	scheduled_hours = flt((entry or {}).get("hours")) or float(mobile_home.STANDARD_DAY_HOURS)
	periods = details.get("periods") or []
	open_period = details.get("open_period")
	events = get_attendance_calendar_events(key, key) or {}

	return {
		"api_version": API_VERSION,
		"date": key,
		"shift": mobile_attendance.shift_window(entry, day),
		"sale_event": _sale_event(schedule.get("events"), key),
		"worked_hours": worked_hours,
		"scheduled_hours": scheduled_hours,
		"overtime_hours": mobile_attendance.day_overtime(worked_hours, scheduled_hours),
		"break_hours": round(sum(flt(row.get("lunch_deduction")) for row in periods), 2),
		"periods": [
			{"start": get_datetime(row["in_time"]).strftime(_TIME_FMT), "end": get_datetime(row["out_time"]).strftime(_TIME_FMT)}
			for row in periods
		],
		"open_period": {"start": get_datetime(open_period["in_time"]).strftime(_TIME_FMT)} if open_period else None,
		"breaks": mobile_attendance.lunch_segments(periods, *_lunch_window(employee.name, day)),
		"punches": _punches(details.get("checkins") or []),
		"anomaly_codes": _anomaly_codes(events.get(key)),
		"has_pending_correction": key in _pending_correction_dates(employee.name, day, day),
	}
