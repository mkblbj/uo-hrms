import frappe
from frappe import _
from frappe.model import get_permitted_fields
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import Order
from frappe.utils import add_days, date_diff, getdate, strip_html

from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

SUPPORTED_FIELD_TYPES = [
	"Link",
	"Select",
	"Small Text",
	"Text",
	"Long Text",
	"Text Editor",
	"Table",
	"Check",
	"Data",
	"Float",
	"Int",
	"Section Break",
	"Date",
	"Time",
	"Datetime",
	"Currency",
]


@frappe.whitelist()
def get_current_user_info() -> dict:
	current_user = frappe.session.user
	user = frappe.db.get_value(
		"User", current_user, ["name", "first_name", "full_name", "user_image"], as_dict=True
	)
	user["roles"] = frappe.get_roles(current_user)

	return user


@frappe.whitelist()
def get_current_employee_info() -> dict:
	current_user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": current_user, "status": "Active"},
		[
			"name",
			"first_name",
			"employee_name",
			"designation",
			"department",
			"company",
			"reports_to",
			"user_id",
		],
		as_dict=True,
	)
	return employee


@frappe.whitelist()
def get_all_employees() -> list[dict]:
	return frappe.get_all(
		"Employee",
		fields=[
			"name",
			"employee_name",
			"designation",
			"department",
			"company",
			"reports_to",
			"user_id",
			"image",
			"status",
		],
		limit=999999,
	)


# HR Settings
@frappe.whitelist()
def get_employee_dashboard_stats() -> dict:
	"""
	获取员工仪表盘统计数据
	包括：本月出勤天数、工作时长、今日打卡记录等
	"""
	from datetime import datetime
	from frappe.utils import get_first_day, get_last_day, now_datetime, time_diff_in_hours
	
	current_user = frappe.session.user
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": current_user, "status": "Active"},
		["name", "employee_name"],
		as_dict=True
	)
	
	if not employee:
		return {}
	
	# 获取本月日期范围
	today = datetime.now().date()
	month_start = get_first_day(today)
	month_end = get_last_day(today)
	
	# 本月出勤统计 + 工时（从 Attendance 表获取，使用班次计算后的 working_hours）
	attendance_stats = frappe.db.sql("""
		SELECT 
			COUNT(*) as total_days,
			SUM(CASE WHEN status IN ('Present', 'Work From Home') THEN 1 ELSE 0 END) as present_days,
			SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) as absent_days,
			SUM(CASE WHEN status = 'On Leave' THEN 1 ELSE 0 END) as leave_days,
			SUM(CASE WHEN status = 'Half Day' THEN 0.5 ELSE 0 END) as half_days,
			SUM(COALESCE(working_hours, 0)) as month_hours
		FROM `tabAttendance`
		WHERE employee = %s 
		AND attendance_date BETWEEN %s AND %s
		AND docstatus = 1
	""", (employee.name, month_start, month_end), as_dict=True)[0]
	
	# 本月总工时（从考勤记录获取，已包含班次的时间舍入和午餐扣除）
	month_hours = float(attendance_stats.month_hours or 0)
	
	# 今日打卡记录
	today_checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee.name,
			"time": [">=", today]
		},
		fields=["log_type", "time"],
		order_by="time asc"
	)
	
	# 今日工时：优先从考勤记录获取，否则实时计算
	today_attendance = frappe.db.get_value(
		"Attendance",
		{"employee": employee.name, "attendance_date": today, "docstatus": 1},
		"working_hours"
	)
	
	if today_attendance:
		today_hours = float(today_attendance)
	else:
		# 还没有考勤记录，实时计算（未扣除午餐）
		today_hours = 0
		if len(today_checkins) >= 2:
			first_in = next((c for c in today_checkins if c.log_type == "IN"), None)
			last_out = next((c for c in reversed(today_checkins) if c.log_type == "OUT"), None)
			
			if first_in and last_out:
				today_hours = time_diff_in_hours(last_out.time, first_in.time)
			elif first_in:
				today_hours = time_diff_in_hours(now_datetime(), first_in.time)
	
	return {
		"employee_name": employee.employee_name,
		"month_present": attendance_stats.present_days or 0,
		"month_absent": attendance_stats.absent_days or 0,
		"month_leave": attendance_stats.leave_days or 0,
		"month_half_days": attendance_stats.half_days or 0,
		"today_hours": round(today_hours, 2),
		"month_hours": round(month_hours, 2),
		"today_checkins": len(today_checkins),
		"first_checkin_today": today_checkins[0].time if today_checkins else None,
		"last_checkin_today": today_checkins[-1].time if today_checkins else None
	}


@frappe.whitelist()
def get_weather_data() -> dict:
	"""
	获取当前天气数据（使用 WeatherAPI.com）
	包含今天的最高/最低温度
	"""
	import requests
	from datetime import datetime
	
	# WeatherAPI 配置
	API_KEY = "a45ee3456cd14c498f681427250405"
	LAT = 34.66497
	LON = 135.15820
	
	# 获取用户语言设置
	user_lang = frappe.local.lang or "ja"
	lang_map = {
		"zh": "zh",
		"ja": "ja",
		"en": "en"
	}
	weather_lang = lang_map.get(user_lang, "ja")
	
	try:
		# 使用 forecast API 获取今天的最高/最低温
		today = datetime.now().strftime("%Y-%m-%d")
		url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={LAT},{LON}&dt={today}&lang={weather_lang}&aqi=no"
		response = requests.get(url, timeout=5)
		response.raise_for_status()
		data = response.json()
		
		current = data["current"]
		today_forecast = data["forecast"]["forecastday"][0]["day"] if data.get("forecast") and data["forecast"].get("forecastday") else None
		
		result = {
			"temp_c": current["temp_c"],
			"condition": {
				"text": current["condition"]["text"],
				"icon": f"https:{current['condition']['icon']}"
			}
		}
		
		# 如果有今天的预报数据，添加最高/最低温
		if today_forecast:
			result["maxtemp_c"] = today_forecast["maxtemp_c"]
			result["mintemp_c"] = today_forecast["mintemp_c"]
		
		return result
	except Exception as e:
		frappe.log_error(f"Weather API Error: {str(e)}", "Weather Widget")
		return None


@frappe.whitelist()
def get_weather_forecast() -> dict:
	"""
	获取明天的天气预报（使用 WeatherAPI.com）
	"""
	import requests
	from datetime import datetime, timedelta
	
	# WeatherAPI 配置
	API_KEY = "a45ee3456cd14c498f681427250405"
	LAT = 34.66497
	LON = 135.15820
	
	# 获取用户语言设置
	user_lang = frappe.local.lang or "ja"
	lang_map = {
		"zh": "zh",
		"ja": "ja",
		"en": "en"
	}
	weather_lang = lang_map.get(user_lang, "ja")
	
	try:
		# 获取明天的日期
		tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
		
		url = f"http://api.weatherapi.com/v1/forecast.json?key={API_KEY}&q={LAT},{LON}&dt={tomorrow}&lang={weather_lang}&aqi=no"
		response = requests.get(url, timeout=5)
		response.raise_for_status()
		data = response.json()
		
		if data.get("forecast") and data["forecast"].get("forecastday"):
			day_data = data["forecast"]["forecastday"][0]["day"]
			return {
				"maxtemp_c": day_data["maxtemp_c"],
				"mintemp_c": day_data["mintemp_c"],
				"condition": {
					"text": day_data["condition"]["text"],
					"icon": f"https:{day_data['condition']['icon']}"
				}
			}
		return None
	except Exception as e:
		frappe.log_error(f"Weather Forecast API Error: {str(e)}", "Weather Widget")
		return None


@frappe.whitelist()
def get_employee_work_status():
	"""
	获取当前员工的工作状态（是否正在上班）
	基于最后一次打卡记录判断：
	- 如果最后一次是 IN，则认为正在上班
	- 如果最后一次是 OUT，则认为不在上班
	- 如果今天没有打卡，则认为不在上班
	"""
	from frappe.utils import today, now_datetime
	
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name"],
		as_dict=True
	)
	
	if not employee:
		return {
			"is_working": False,
			"status": "not_employee",
			"last_checkin": None
		}
	
	# 获取今天最后一次打卡记录
	last_checkin = frappe.db.get_all(
		"Employee Checkin",
		filters={
			"employee": employee.name,
			"time": [">=", today()]
		},
		fields=["name", "log_type", "time"],
		order_by="time desc",
		limit=1
	)
	
	if not last_checkin:
		return {
			"is_working": False,
			"status": "no_checkin_today",
			"last_checkin": None,
			"employee_name": employee.employee_name
		}
	
	last_log = last_checkin[0]
	is_working = last_log.log_type == "IN"
	
	return {
		"is_working": is_working,
		"status": "working" if is_working else "off_work",
		"last_checkin": {
			"log_type": last_log.log_type,
			"time": str(last_log.time)
		},
		"employee_name": employee.employee_name
	}


@frappe.whitelist()
def get_hr_settings() -> dict:
	settings = frappe.db.get_singles_dict("HR Settings", cast=True)
	return frappe._dict(
		allow_employee_checkin_from_mobile_app=settings.allow_employee_checkin_from_mobile_app,
		allow_geolocation_tracking=settings.allow_geolocation_tracking,
	)


# Notifications
@frappe.whitelist()
def get_unread_notifications_count() -> int:
	return frappe.db.count(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
	)


@frappe.whitelist()
def mark_all_notifications_as_read() -> None:
	frappe.db.set_value(
		"PWA Notification",
		{"to_user": frappe.session.user, "read": 0},
		"read",
		1,
		update_modified=False,
	)


@frappe.whitelist()
def are_push_notifications_enabled() -> bool:
	try:
		return frappe.db.get_single_value("Push Notification Settings", "enable_push_notification_relay")
	except frappe.DoesNotExistError:
		# push notifications are not supported in the current framework version
		return False


# Attendance
@frappe.whitelist()
def get_attendance_calendar_events(employee: str, from_date: str, to_date: str) -> dict:
	holidays = get_holidays_for_calendar(employee, from_date, to_date)
	attendance = get_attendance_for_calendar(employee, from_date, to_date)
	shifts = get_shifts_for_calendar(employee, from_date, to_date)
	events = {}

	date = getdate(from_date)
	while date_diff(to_date, date) >= 0:
		date_str = date.strftime("%Y-%m-%d")
		event = {}
		
		# 考勤状态和签到签退记录
		if date in attendance:
			att = attendance[date]
			event["attendance"] = att["status"]
			event["in_time"] = att["in_time"]
			event["out_time"] = att["out_time"]
			event["working_hours"] = att["working_hours"]
		elif date in holidays:
			event["attendance"] = "Holiday"
		
		# 排班信息
		if date_str in shifts:
			event["shift"] = shifts[date_str]
		
		if event:
			events[date_str] = event
		date = add_days(date, 1)

	return events


def get_attendance_for_calendar(employee: str, from_date: str, to_date: str) -> dict:
	attendance = frappe.get_all(
		"Attendance",
		{"employee": employee, "attendance_date": ["between", [from_date, to_date]], "docstatus": 1},
		["attendance_date", "status", "in_time", "out_time", "working_hours"],
	)
	result = {}
	for d in attendance:
		# in_time 和 out_time 是 datetime 格式，需要提取时间部分
		in_time = None
		out_time = None
		if d["in_time"]:
			in_time = str(d["in_time"])[11:16] if len(str(d["in_time"])) > 11 else str(d["in_time"])[:5]
		if d["out_time"]:
			out_time = str(d["out_time"])[11:16] if len(str(d["out_time"])) > 11 else str(d["out_time"])[:5]
		
		result[d["attendance_date"]] = {
			"status": d["status"],
			"in_time": in_time,
			"out_time": out_time,
			"working_hours": d["working_hours"]
		}
	return result


def get_holidays_for_calendar(employee: str, from_date: str, to_date: str) -> list[str]:
	if holiday_list := get_holiday_list_for_employee(employee, raise_exception=False):
		return frappe.get_all(
			"Holiday",
			filters={"parent": holiday_list, "holiday_date": ["between", [from_date, to_date]]},
			pluck="holiday_date",
		)

	return []


def get_shifts_for_calendar(employee: str, from_date: str, to_date: str) -> dict:
	"""获取指定日期范围内的排班信息"""
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	
	shifts = (
		frappe.qb.select(
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftType.name.as_("shift_type"),
			ShiftType.start_time,
			ShiftType.end_time,
			ShiftType.color,
		)
		.from_(ShiftAssignment)
		.join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.where(
			(ShiftAssignment.employee == employee)
			& (ShiftAssignment.status == "Active")
			& (ShiftAssignment.docstatus == 1)
			& (ShiftAssignment.start_date <= to_date)
			& ((ShiftAssignment.end_date >= from_date) | (ShiftAssignment.end_date.isnull()))
		)
	).run(as_dict=True)
	
	result = {}
	for shift in shifts:
		start_date = getdate(shift.start_date)
		end_date = getdate(shift.end_date) if shift.end_date else getdate(to_date)
		to_date_obj = getdate(to_date)
		
		date = start_date
		while date <= end_date and date <= to_date_obj:
			if date >= getdate(from_date):
				date_str = date.strftime("%Y-%m-%d")
				result[date_str] = {
					"shift_type": shift.shift_type,
					"start_time": str(shift.start_time) if shift.start_time else None,
					"end_time": str(shift.end_time) if shift.end_time else None,
					"color": shift.color,
				}
			date = add_days(date, 1)
	
	return result


@frappe.whitelist()
def get_shift_requests(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Shift Request", employee, approver_id, for_approval)
	fields = [
		"name",
		"employee",
		"employee_name",
		"shift_type",
		"from_date",
		"to_date",
		"status",
		"approver",
		"docstatus",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Shift Request"):
		fields.append(workflow_state_field)

	shift_requests = frappe.get_list(
		"Shift Request",
		fields=fields,
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in shift_requests:
			application["workflow_state_field"] = workflow_state_field

	return shift_requests


@frappe.whitelist()
def get_attendance_requests(
	employee: str,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Attendance Request", employee, None, for_approval)
	fields = [
		"name",
		"reason",
		"employee",
		"employee_name",
		"from_date",
		"to_date",
		"include_holidays",
		"shift",
		"docstatus",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Attendance Request"):
		fields.append(workflow_state_field)

	attendance_requests = frappe.get_list(
		"Attendance Request",
		fields=fields,
		filters=filters,
		order_by="creation desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in attendance_requests:
			application["workflow_state_field"] = workflow_state_field

	return attendance_requests


def get_filters(
	doctype: str,
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
) -> dict:
	filters = frappe._dict()
	if for_approval:
		filters.docstatus = 0
		filters.employee = ("!=", employee)

		if workflow := get_workflow(doctype):
			allowed_states = get_allowed_states_for_workflow(workflow, approver_id)
			filters[workflow.workflow_state_field] = ("in", allowed_states)
		elif doctype != "Attendance Request":
			approver_field_map = {
				"Shift Request": "approver",
				"Leave Application": "leave_approver",
				"Expense Claim": "expense_approver",
			}
			filters.status = "Open" if doctype == "Leave Application" else "Draft"
			if approver_id:
				filters[approver_field_map[doctype]] = approver_id
	else:
		filters.docstatus = ("!=", 2)
		filters.employee = employee

	return filters


@frappe.whitelist()
def get_shift_request_approvers(employee: str) -> str | list[str]:
	shift_request_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["shift_request_approver", "department"],
	)

	department_approvers = []
	if department:
		department_approvers = get_department_approvers(department, "shift_request_approver")
		if not shift_request_approver:
			shift_request_approver = frappe.db.get_value(
				"Department Approver",
				{"parent": department, "parentfield": "shift_request_approver", "idx": 1},
				"approver",
			)

	shift_request_approver_name = frappe.db.get_value("User", shift_request_approver, "full_name", cache=True)

	if shift_request_approver and shift_request_approver not in [
		approver.name for approver in department_approvers
	]:
		department_approvers.insert(
			0, {"name": shift_request_approver, "full_name": shift_request_approver_name}
		)

	return department_approvers


@frappe.whitelist()
def get_shifts(employee: str) -> list[dict[str, str]]:
	ShiftAssignment = frappe.qb.DocType("Shift Assignment")
	ShiftType = frappe.qb.DocType("Shift Type")
	return (
		frappe.qb.from_(ShiftAssignment)
		.join(ShiftType)
		.on(ShiftAssignment.shift_type == ShiftType.name)
		.select(
			ShiftAssignment.name,
			ShiftAssignment.shift_type,
			ShiftAssignment.start_date,
			ShiftAssignment.end_date,
			ShiftType.start_time,
			ShiftType.end_time,
		)
		.where(
			(ShiftAssignment.employee == employee)
			& (ShiftAssignment.status == "Active")
			& (ShiftAssignment.docstatus == 1)
		)
		.orderby(ShiftAssignment.start_date, order=Order.asc)
	).run(as_dict=True)


# Leaves and Holidays
@frappe.whitelist()
def get_leave_applications(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Leave Application", employee, approver_id, for_approval)
	fields = [
		"name",
		"posting_date",
		"employee",
		"employee_name",
		"leave_type",
		"status",
		"from_date",
		"to_date",
		"half_day",
		"half_day_date",
		"description",
		"total_leave_days",
		"leave_balance",
		"leave_approver",
		"posting_date",
		"creation",
	]

	if workflow_state_field := get_workflow_state_field("Leave Application"):
		fields.append(workflow_state_field)

	applications = frappe.get_list(
		"Leave Application",
		fields=fields,
		filters=filters,
		order_by="posting_date desc",
		limit=limit,
	)

	if workflow_state_field:
		for application in applications:
			application["workflow_state_field"] = workflow_state_field

	return applications


@frappe.whitelist()
def get_leave_balance_map(employee: str) -> dict[str, dict[str, float]]:
	"""
	Returns a map of leave type and balance details like:
	{
	        'Casual Leave': {'allocated_leaves': 10.0, 'balance_leaves': 5.0},
	        'Earned Leave': {'allocated_leaves': 3.0, 'balance_leaves': 3.0},
	}
	"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = getdate()
	leave_map = {}

	leave_details = get_leave_details(employee, date)
	allocation = leave_details["leave_allocation"]

	for leave_type, details in allocation.items():
		leave_map[leave_type] = {
			"allocated_leaves": details.get("total_leaves"),
			"balance_leaves": details.get("remaining_leaves"),
		}

	return leave_map


@frappe.whitelist()
def get_holidays_for_employee(employee: str) -> list[dict]:
	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return []

	Holiday = frappe.qb.DocType("Holiday")
	holidays = (
		frappe.qb.from_(Holiday)
		.select(Holiday.name, Holiday.holiday_date, Holiday.description)
		.where((Holiday.parent == holiday_list) & (Holiday.weekly_off == 0))
		.orderby(Holiday.holiday_date, order=Order.asc)
	).run(as_dict=True)

	for holiday in holidays:
		holiday["description"] = strip_html(holiday["description"] or "").strip()

	return holidays


@frappe.whitelist()
def get_leave_approval_details(employee: str) -> dict:
	leave_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["leave_approver", "department"],
	)

	if not leave_approver and department:
		leave_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "leave_approvers", "idx": 1},
			"approver",
		)

	leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name", cache=True)
	department_approvers = get_department_approvers(department, "leave_approvers")

	if leave_approver and leave_approver not in [approver.name for approver in department_approvers]:
		department_approvers.append({"name": leave_approver, "full_name": leave_approver_name})

	return dict(
		leave_approver=leave_approver,
		leave_approver_name=leave_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value(
			"HR Settings", "leave_approver_mandatory_in_leave_application"
		),
	)


def get_department_approvers(department: str, parentfield: str) -> list[str]:
	if not department:
		return []

	department_details = frappe.db.get_value("Department", department, ["lft", "rgt"], as_dict=True)
	departments = frappe.get_all(
		"Department",
		filters={
			"lft": ("<=", department_details.lft),
			"rgt": (">=", department_details.rgt),
			"disabled": 0,
		},
		pluck="name",
	)

	Approver = frappe.qb.DocType("Department Approver")
	User = frappe.qb.DocType("User")
	department_approvers = (
		frappe.qb.from_(User)
		.join(Approver)
		.on(Approver.approver == User.name)
		.select(User.name.as_("name"), User.full_name.as_("full_name"))
		.where((Approver.parent.isin(departments)) & (Approver.parentfield == parentfield))
	).run(as_dict=True)

	return department_approvers


@frappe.whitelist()
def get_leave_types(employee: str, date: str) -> list:
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	date = date or getdate()

	leave_details = get_leave_details(employee, date)
	leave_types = list(leave_details["leave_allocation"].keys()) + leave_details["lwps"]

	return leave_types


# Expense Claims
@frappe.whitelist()
def get_expense_claims(
	employee: str,
	approver_id: str | None = None,
	for_approval: bool = False,
	limit: int | None = None,
) -> list[dict]:
	filters = get_filters("Expense Claim", employee, approver_id, for_approval)
	fields = [
		"`tabExpense Claim`.name",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.employee",
		"`tabExpense Claim`.employee_name",
		"`tabExpense Claim`.approval_status",
		"`tabExpense Claim`.status",
		"`tabExpense Claim`.expense_approver",
		"`tabExpense Claim`.total_claimed_amount",
		"`tabExpense Claim`.posting_date",
		"`tabExpense Claim`.company",
		"`tabExpense Claim`.creation",
		"`tabExpense Claim Detail`.expense_type",
		"count(`tabExpense Claim Detail`.expense_type) as total_expenses",
	]

	if workflow_state_field := get_workflow_state_field("Expense Claim"):
		fields.append(workflow_state_field)

	claims = frappe.get_list(
		"Expense Claim",
		fields=fields,
		filters=filters,
		order_by="`tabExpense Claim`.posting_date desc",
		group_by="`tabExpense Claim`.name",
		limit=limit,
	)

	if workflow_state_field:
		for claim in claims:
			claim["workflow_state_field"] = workflow_state_field

	return claims


@frappe.whitelist()
def get_expense_claim_summary(employee: str) -> dict:
	from frappe.query_builder.functions import Sum

	Claim = frappe.qb.DocType("Expense Claim")

	pending_claims_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Draft", Claim.total_claimed_amount).else_(0)
	)
	sum_pending_claims = Sum(pending_claims_case).as_("total_pending_amount")

	approved_claims_case = (
		frappe.qb.terms.Case()
		.when(Claim.approval_status == "Approved", Claim.total_sanctioned_amount)
		.else_(0)
	)
	sum_approved_claims = Sum(approved_claims_case).as_("total_approved_amount")

	approved_total_claimed_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Approved", Claim.total_claimed_amount).else_(0)
	)
	sum_approved_total_claimed = Sum(approved_total_claimed_case).as_("total_claimed_in_approved")

	rejected_claims_case = (
		frappe.qb.terms.Case().when(Claim.approval_status == "Rejected", Claim.total_claimed_amount).else_(0)
	)
	sum_rejected_claims = Sum(rejected_claims_case).as_("total_rejected_amount")

	summary = (
		frappe.qb.from_(Claim)
		.select(
			sum_pending_claims,
			sum_approved_claims,
			sum_rejected_claims,
			sum_approved_total_claimed,
			Claim.company,
		)
		.where((Claim.docstatus != 2) & (Claim.employee == employee))
	).run(as_dict=True)[0]

	currency = frappe.db.get_value("Company", summary.company, "default_currency")
	summary["currency"] = currency

	return summary


@frappe.whitelist()
def get_expense_type_description(expense_type: str) -> str:
	return frappe.db.get_value("Expense Claim Type", expense_type, "description")


@frappe.whitelist()
def get_expense_claim_types() -> list[dict]:
	ClaimType = frappe.qb.DocType("Expense Claim Type")

	return (frappe.qb.from_(ClaimType).select(ClaimType.name, ClaimType.description)).run(as_dict=True)


@frappe.whitelist()
def get_expense_approval_details(employee: str) -> dict:
	expense_approver, department = frappe.get_cached_value(
		"Employee",
		employee,
		["expense_approver", "department"],
	)

	if not expense_approver and department:
		expense_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "expense_approvers", "idx": 1},
			"approver",
		)

	expense_approver_name = frappe.db.get_value("User", expense_approver, "full_name", cache=True)
	department_approvers = get_department_approvers(department, "expense_approvers")

	if expense_approver and expense_approver not in [approver.name for approver in department_approvers]:
		department_approvers.append({"name": expense_approver, "full_name": expense_approver_name})

	return dict(
		expense_approver=expense_approver,
		expense_approver_name=expense_approver_name,
		department_approvers=department_approvers,
		is_mandatory=frappe.db.get_single_value("HR Settings", "expense_approver_mandatory_in_expense_claim"),
	)


# Employee Advance
@frappe.whitelist()
def get_employee_advance_balance(employee: str) -> list[dict]:
	Advance = frappe.qb.DocType("Employee Advance")

	advances = (
		frappe.qb.from_(Advance)
		.select(
			Advance.name,
			Advance.employee,
			Advance.status,
			Advance.purpose,
			Advance.paid_amount,
			(Advance.paid_amount - (Advance.claimed_amount + Advance.return_amount)).as_("balance_amount"),
			Advance.posting_date,
			Advance.currency,
		)
		.where(
			(Advance.docstatus == 1)
			& (Advance.paid_amount)
			& (Advance.employee == employee)
			# don't need claimed & returned advances, only partly or completely paid ones
			& (Advance.status.isin(["Paid", "Unpaid"]))
		)
		.orderby(Advance.posting_date, order=Order.desc)
	).run(as_dict=True)

	return advances


@frappe.whitelist()
def get_advance_account(company: str) -> str | None:
	return frappe.db.get_value("Company", company, "default_employee_advance_account", cache=True)


# Company
@frappe.whitelist()
def get_company_currencies() -> dict:
	Company = frappe.qb.DocType("Company")
	Currency = frappe.qb.DocType("Currency")

	query = (
		frappe.qb.from_(Company)
		.join(Currency)
		.on(Company.default_currency == Currency.name)
		.select(
			Company.name,
			Company.default_currency,
			Currency.name.as_("currency"),
			Currency.symbol.as_("symbol"),
		)
	)

	companies = query.run(as_dict=True)
	return {company.name: (company.default_currency, company.symbol) for company in companies}


@frappe.whitelist()
def get_currency_symbols() -> dict:
	Currency = frappe.qb.DocType("Currency")

	currencies = (frappe.qb.from_(Currency).select(Currency.name, Currency.symbol)).run(as_dict=True)

	return {currency.name: currency.symbol or currency.name for currency in currencies}


@frappe.whitelist()
def get_company_cost_center_and_expense_account(company: str) -> dict:
	return frappe.db.get_value(
		"Company", company, ["cost_center", "default_expense_claim_payable_account"], as_dict=True
	)


# Form View APIs
@frappe.whitelist()
def get_doctype_fields(doctype: str) -> list[dict]:
	fields = frappe.get_meta(doctype).fields
	return [
		field
		for field in fields
		if field.fieldtype in SUPPORTED_FIELD_TYPES and field.fieldname != "amended_from"
	]


@frappe.whitelist()
def get_doctype_states(doctype: str) -> dict:
	states = frappe.get_meta(doctype).states
	return {state.title: state.color.lower() for state in states}


# File
@frappe.whitelist()
def get_attachments(dt: str, dn: str):
	from frappe.desk.form.load import get_attachments

	return get_attachments(dt, dn)


@frappe.whitelist()
def upload_base64_file(content, filename, dt=None, dn=None, fieldname=None):
	import base64
	import io
	from mimetypes import guess_type

	from PIL import Image, ImageOps

	from frappe.handler import ALLOWED_MIMETYPES

	decoded_content = base64.b64decode(content)
	content_type = guess_type(filename)[0]
	if content_type not in ALLOWED_MIMETYPES:
		frappe.throw(_("You can only upload JPG, PNG, PDF, TXT or Microsoft documents."))

	if content_type.startswith("image/jpeg"):
		# transpose the image according to the orientation tag, and remove the orientation data
		with Image.open(io.BytesIO(decoded_content)) as image:
			transpose_img = ImageOps.exif_transpose(image)
			# convert the image back to bytes
			file_content = io.BytesIO()
			transpose_img.save(file_content, format="JPEG")
			file_content = file_content.getvalue()
	else:
		file_content = decoded_content

	return frappe.get_doc(
		{
			"doctype": "File",
			"attached_to_doctype": dt,
			"attached_to_name": dn,
			"attached_to_field": fieldname,
			"folder": "Home",
			"file_name": filename,
			"content": file_content,
			"is_private": 1,
		}
	).insert()


@frappe.whitelist()
def delete_attachment(filename: str):
	frappe.delete_doc("File", filename)


@frappe.whitelist()
def _download_pdf(doctype: str, docname: str) -> str:
	import base64

	from frappe.utils.print_format import download_pdf

	default_print_format = frappe.get_meta(doctype).default_print_format or "Standard"

	try:
		download_pdf(doctype, docname, format=default_print_format)
	except Exception as e:
		frappe.throw(_("Failed to download PDF: {0}").format(str(e)))

	base64content = base64.b64encode(frappe.local.response.filecontent)
	content_type = frappe.local.response.type

	return f"data:{content_type};base64," + base64content.decode("utf-8")


# Latest Notification
@frappe.whitelist()
def get_latest_notification() -> dict:
	"""获取当前用户的最新一条通知"""
	user = frappe.session.user
	
	notification = frappe.db.get_value(
		"PWA Notification",
		{"to_user": user},
		["name", "message", "from_user", "creation", "read", "use_html_source", "html_source"],
		order_by="creation desc",
		as_dict=True
	)
	
	if notification:
		# 根据 use_html_source 选择显示内容
		if notification.get("use_html_source") and notification.get("html_source"):
			notification["display_message"] = notification["html_source"]
		else:
			notification["display_message"] = notification["message"]
		return notification
	
	return frappe._dict()


# Workflow
@frappe.whitelist()
def get_workflow(doctype: str) -> dict:
	workflow = get_workflow_name(doctype)
	if not workflow:
		return frappe._dict()
	return frappe.get_doc("Workflow", workflow)


def get_workflow_state_field(doctype: str) -> str | None:
	workflow_name = get_workflow_name(doctype)
	if not workflow_name:
		return None

	override_status, workflow_state_field = frappe.db.get_value(
		"Workflow",
		workflow_name,
		["override_status", "workflow_state_field"],
	)
	# NOTE: checkbox labelled 'Don't Override Status' is named override_status hence the inverted logic
	if not override_status:
		return workflow_state_field
	return None


def get_allowed_states_for_workflow(workflow: dict, user_id: str) -> list[str]:
	user_roles = frappe.get_roles(user_id)
	return [transition.state for transition in workflow.transitions if transition.allowed in user_roles]


# Permissions
@frappe.whitelist()
def get_permitted_fields_for_write(doctype: str) -> list[str]:
	return get_permitted_fields(doctype, permission_type="write")


# QR Attendance - 动态二维码打卡
from hrms.api.qr_attendance import (
	generate_qr_token,
	qr_checkin,
	get_checkin_locations
)

# Passkey/WebAuthn - NFC 打卡
from hrms.api.passkey import (
	register_options as passkey_register_options,
	register_complete as passkey_register_complete,
	auth_options as passkey_auth_options,
	passkey_checkin,
	get_my_passkeys,
	delete_passkey,
	check_passkey_registered,
)
