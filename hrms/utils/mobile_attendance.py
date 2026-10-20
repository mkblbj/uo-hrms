"""原生 App 勤怠页的计算规则（PWA attendanceCalendarState.js 加 M2 的新规则）。

只做纯计算，不读数据库；数据由 hrms.api.mobile 取好再传进来。
"""

import math
from datetime import date

from hrms.utils.mobile_home import OVERTIME_THRESHOLD_HOURS, STANDARD_DAY_HOURS

STATES = (
	"work",
	"overtime",
	"anomaly",
	"working",
	"checked_out",
	"leave",
	"rest",
	"holiday",
	"scheduled",
	"empty",
)
_WORK_STATUSES = ("Present", "Work From Home", "Half Day")
# 真实考勤记录的状态；Holiday 是月历接口按假日表合成的，不是考勤记录
_RECORD_STATUSES = (*_WORK_STATUSES, "On Leave", "Absent")
_SETTLED_WORK = ("work", "overtime")


def round1(value) -> float:
	# 和 JS 的 Math.round(x * 10) / 10 一样四舍五入（Python 的 round 是银行家舍入）
	return math.floor(float(value) * 10 + 0.5) / 10


def _status(event: dict | None) -> str:
	return (event or {}).get("attendance") or ""


def day_hours(event: dict | None) -> float | None:
	"""有考勤记录且工时大于 0 时，返回取到一位小数的工时。"""
	if _status(event) not in _RECORD_STATUSES:
		return None
	try:
		hours = float((event or {}).get("working_hours") or 0)
	except (TypeError, ValueError):
		return None
	return round1(hours) if hours > 0 else None


def day_weight(event: dict | None) -> float:
	status = _status(event)
	if status in ("Present", "Work From Home"):
		return 1
	return 0.5 if status == "Half Day" else 0


def leave_weight(event: dict | None) -> float:
	status = _status(event)
	if status == "On Leave":
		return 1
	return 0.5 if status == "Half Day" else 0


def day_overtime(hours: float | None, scheduled_hours: float | None) -> float:
	"""实际工作减所定（没有排班按 8 小时），不足 0 记 0。"""
	if hours is None:
		return 0
	return round1(max(0.0, hours - float(scheduled_hours or STANDARD_DAY_HOURS)))


def derive_day_state(event: dict | None, holiday: dict | None, roster: dict | None, day: date, today: date) -> str:
	event = event or {}
	if (event.get("anomaly") or {}).get("has_issue"):
		return "anomaly"
	if event.get("checkin_status") in ("working", "checked_out"):
		return event["checkin_status"]

	status = _status(event)
	if status in _WORK_STATUSES:
		overtime = day_overtime(day_hours(event), (roster or {}).get("hours"))
		return "overtime" if overtime >= OVERTIME_THRESHOLD_HOURS else "work"
	if status == "On Leave":
		return "leave"
	if status == "Absent":
		# 和 PWA 一样，缺勤先显示成休息
		return "rest"

	if roster and day >= today:
		return "scheduled"
	if holiday or status == "Holiday":
		return "rest" if (holiday or {}).get("weekly_off") else "holiday"
	return "empty"


def summarize_month(days: list[dict], scheduled_days: int | None, remaining_days: int | None) -> dict:
	"""days 里每天带内部字段 _weight、_leave、_overtime；工时和出勤只算已结算的工作日。"""
	settled = [row for row in days if row["state"] in _SETTLED_WORK]
	return {
		"hours": round1(sum(row["hours"] or 0 for row in settled)),
		"present_days": round1(sum(row["_weight"] for row in settled)),
		"scheduled_days": scheduled_days,
		"remaining_days": remaining_days,
		"overtime_hours": round1(sum(row["_overtime"] for row in settled)),
		"leave_days": round1(sum(row["_leave"] for row in days)),
		"issue_count": sum(1 for row in days if row["state"] == "anomaly"),
	}
