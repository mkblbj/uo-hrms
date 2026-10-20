"""原生 App 排班页（M3）的计算规则。

只做纯计算，不读数据库；排班条目、假日、大促由 hrms.api.mobile 取好再传进来。
"""

import re
from datetime import date, datetime, timedelta

from frappe.utils import strip_html_tags

from hrms.utils.mobile_attendance import round1
from hrms.utils.mobile_home import URGENT_DEADLINE_DAYS

_FMT = "%Y-%m-%d %H:%M:%S"
_CLOCK_RE = re.compile(r"(\d{1,2}):(\d{2})")
_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def week_bounds(day: date) -> tuple[date, date]:
	"""包含这一天的那一周：周一、周日。"""
	monday = day - timedelta(days=day.isoweekday() - 1)
	return monday, monday + timedelta(days=6)


def clock(value) -> str | None:
	"""time / timedelta / "9:30:00" → "09:30"；空值为 None。"""
	match = _CLOCK_RE.search(str(value)) if value not in (None, "") else None
	return f"{int(match.group(1)):02d}:{match.group(2)}" if match else None


def shift_window(day: date, start: str | None, end: str | None) -> tuple[str, str] | None:
	"""HH:MM → 时间点；结束早于开始时算第二天（同 work_roster 的 _build_work_interval）。"""
	if not start or not end:
		return None
	start_at = datetime.fromisoformat(f"{day.isoformat()} {start}:00")
	end_at = datetime.fromisoformat(f"{day.isoformat()} {end}:00")
	if end_at < start_at:
		end_at += timedelta(days=1)
	return start_at.strftime(_FMT), end_at.strftime(_FMT)


def normalize_color(value) -> str | None:
	"""#RRGGBB（大写）；没设置或不是 6 位十六进制时为 None。"""
	text = str(value or "").strip()
	return text.upper() if _COLOR_RE.fullmatch(text) else None


def day_fields(day: date, holiday: dict | None, sale_event: dict | None) -> dict:
	"""一天的公共字段；holiday 为 {description, weekly_off}，周休不算祝日名。"""
	weekly_off = bool(holiday and holiday.get("weekly_off"))
	name = None
	if holiday and not weekly_off:
		name = strip_html_tags(holiday.get("description") or "").strip() or None
	return {
		"date": day.isoformat(),
		"weekday": day.isoweekday(),
		"holiday_name": name,
		"is_weekly_off": weekly_off,
		"sale_event": sale_event,
	}


def totals(days: list[dict]) -> dict:
	"""有排班的天数和时长之和（一位小数）。"""
	hours = [day["shift"]["hours"] for day in days if day.get("shift")]
	return {"shift_days": len(hours), "hours": round1(sum(hours))}


def deadline_status(deadline: date | None, today: date) -> tuple[int | None, bool]:
	"""(离截止还剩几天, 是否紧急)；已过期为负数且算紧急，没有截止日为 (None, False)。"""
	if not deadline:
		return None, False
	remaining = (deadline - today).days
	return remaining, remaining <= URGENT_DEADLINE_DAYS


def employee_sort_key(row: dict) -> tuple:
	"""按班次开始、结束、姓名、编号排；没有起止时间的排最后。"""
	shift = row.get("shift") or {}
	return (
		shift.get("start") is None,
		shift.get("start") or "",
		shift.get("end") or "",
		row.get("employee_name") or "",
		row.get("employee") or "",
	)
