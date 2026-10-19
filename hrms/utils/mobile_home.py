"""原生 App 主页的计算规则（从 PWA 前端搬来，PWA 的 node:test 用例是规格）。

只做纯计算，不读数据库；数据由 hrms.api.mobile 取好再传进来。
"""

import math
import re
from datetime import date, datetime, time, timedelta

STANDARD_DAY_HOURS = 8
HEATMAP_WEEKS = 20
_ATTENDED = ("Present", "Work From Home", "Half Day")


def _iso(day: date) -> str:
	return day.isoformat()


def _level_for_ratio(ratio: float) -> int:
	if ratio <= 0:
		return 0
	if ratio < 0.5:
		return 1
	if ratio < 0.75:
		return 2
	if ratio < 1:
		return 3
	if ratio < 1.25:
		return 4
	return 5


def _fallback_hours(status: str) -> float:
	if status == "Half Day":
		return STANDARD_DAY_HOURS * 0.5
	if status in ("Present", "Work From Home"):
		return STANDARD_DAY_HOURS
	return 0


def heatmap_cell(event: dict | None, day: date, today: date) -> dict:
	"""一天的格子：档位 0–5，以及今天 / 未来 / 要确认的标记（homeHeatmap.js getAttendanceHeatmapCellMeta）。"""
	is_future = day > today
	is_today = day == today
	status = (event or {}).get("attendance") or ""
	hours = (event or {}).get("working_hours")
	hours = float(_fallback_hours(status) if hours is None else hours)
	cell = {
		"date": _iso(day),
		"weekday": day.isoweekday(),
		"level": 0,
		"is_today": is_today,
		"is_future": is_future,
		"has_issue": False,
		"today_status": None,
	}

	anomaly = (event or {}).get("anomaly") or {}
	if anomaly.get("has_issue") and not is_future and not is_today:
		cell["has_issue"] = True
		return cell
	if is_future:
		return cell

	checkin_status = (event or {}).get("checkin_status")
	if is_today and checkin_status in ("working", "checked_out"):
		cell["level"] = 1
		cell["today_status"] = checkin_status
		return cell

	if not event or not (status in _ATTENDED or hours > 0):
		return cell

	cell["level"] = _level_for_ratio(hours / STANDARD_DAY_HOURS)
	return cell


def heatmap_range(today: date, weeks: int = HEATMAP_WEEKS) -> tuple[date, date]:
	"""返回（第一周的周一，本周周日）。"""
	this_monday = today - timedelta(days=today.isoweekday() - 1)
	return this_monday - timedelta(weeks=weeks - 1), this_monday + timedelta(days=6)


def heatmap_cells(events: dict[str, dict], today: date, weeks: int = HEATMAP_WEEKS) -> list[dict]:
	"""按周排列（每周周一到周日）的全部格子，最后一周是本周。"""
	start, _ = heatmap_range(today, weeks)
	cells = []
	for offset in range(weeks * 7):
		day = start + timedelta(days=offset)
		cells.append(heatmap_cell(events.get(_iso(day)), day, today))
	return cells


def heatmap_month_markers(cells: list[dict]) -> list[dict]:
	"""第一周和月份变化的那一周标月份（取每周周一的月份）。"""
	markers = []
	previous = None
	for week, index in enumerate(range(0, len(cells), 7)):
		month = int(cells[index]["date"][5:7])
		if previous is None or month != previous:
			markers.append({"week": week, "month": month})
		previous = month
	return markers


# ---- 今日进度（homeShiftProgress.js）----

LUNCH_START = time(12, 0)
LUNCH_END = time(13, 0)
OVERTIME_THRESHOLD_HOURS = 0.5
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")
_FMT = "%Y-%m-%d %H:%M:%S"


def _round2(value: float) -> float:
	# 和 JS 的 Math.round(x * 100) / 100 一样四舍五入（Python 的 round 是银行家舍入）
	return math.floor(value * 100 + 0.5) / 100


def _clock(text) -> str:
	match = _TIME_RE.search(str(text or ""))
	return f"{int(match.group(1)):02d}:{match.group(2)}" if match else ""


def _schedule_clock(entry: dict, key: str) -> str:
	direct = _clock(entry.get(key))
	if direct:
		return direct
	parts = str(entry.get("scheduled_time") or "").split("-")
	index = 0 if key == "start_time" else 1
	return _clock(parts[index]) if len(parts) > index else ""


def _parse_dt(value) -> datetime | None:
	if not value:
		return None
	if isinstance(value, datetime):
		return value
	try:
		return datetime.fromisoformat(str(value).strip())
	except ValueError:
		return None


def _lunch_windows(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
	"""区间内每一天的午休，只取与区间重叠的部分。"""
	windows = []
	day = start.date()
	while day <= end.date():
		lunch_start = datetime.combine(day, LUNCH_START)
		lunch_end = datetime.combine(day, LUNCH_END)
		overlap_start, overlap_end = max(start, lunch_start), min(end, lunch_end)
		if overlap_end > overlap_start:
			windows.append((overlap_start, overlap_end))
		day += timedelta(days=1)
	return windows


def _net_hours(end: datetime, start: datetime) -> float:
	if end <= start:
		return 0
	lunch = sum((b - a).total_seconds() for a, b in _lunch_windows(start, end))
	return max(0, ((end - start).total_seconds() - lunch) / 3600)


def _resolve_status(work_status) -> str:
	if isinstance(work_status, dict) and work_status.get("status"):
		return work_status["status"]
	if isinstance(work_status, bool):
		return "working" if work_status else "off_work"
	if isinstance(work_status, dict) and isinstance(work_status.get("is_working"), bool):
		return "working" if work_status["is_working"] else "off_work"
	return "no_checkin_today"


def _last_checkin_time(work_status, log_type: str) -> datetime | None:
	last = (work_status or {}).get("last_checkin") if isinstance(work_status, dict) else None
	if last and last.get("log_type") == log_type:
		return _parse_dt(last.get("time"))
	return None


def today_progress(entry: dict | None, stats: dict, work_status: dict, now: datetime) -> dict | None:
	"""今日班次的进度；没有可用的班次时返回 None。"""
	if not entry:
		return None
	day = str(entry.get("date") or "")[:10]
	start_text, end_text = _schedule_clock(entry, "start_time"), _schedule_clock(entry, "end_time")
	if not day or not start_text or not end_text:
		return None
	shift_start = datetime.fromisoformat(f"{day} {start_text}:00")
	shift_end = datetime.fromisoformat(f"{day} {end_text}:00")
	if shift_end < shift_start:
		shift_end += timedelta(days=1)

	planned = entry.get("hours")
	shift_hours = None
	if planned not in (None, ""):
		try:
			planned = float(planned)
			if math.isfinite(planned) and planned >= 0:
				shift_hours = planned
		except (TypeError, ValueError):
			pass
	if shift_hours is None:
		shift_hours = _net_hours(shift_end, shift_start)
	if shift_hours <= 0:
		return None

	stats = stats or {}
	status = _resolve_status(work_status)
	actual_start = _parse_dt(stats.get("first_checkin_today")) or _last_checkin_time(work_status, "IN")
	if status == "working":
		actual_end = now
	else:
		actual_end = _parse_dt(stats.get("last_checkin_today")) or _last_checkin_time(work_status, "OUT")

	worked = total = 0.0
	if actual_start and actual_end and actual_end > actual_start:
		bounded_start = max(actual_start, shift_start)
		worked = _net_hours(min(actual_end, shift_end), bounded_start)
		total = _net_hours(actual_end, bounded_start)

	overtime = _round2(max(0, total - worked))
	has_overtime = overtime >= OVERTIME_THRESHOLD_HOURS
	if status == "working":
		status_key = "overtime" if has_overtime else "working"
	elif status == "off_work":
		status_key = "done"
	else:
		status_key = "pending"
	percent = 100 if has_overtime else _round2(min(max(worked / shift_hours * 100, 0), 100))

	return {
		"status_key": status_key,
		"shift_start": shift_start.strftime(_FMT),
		"shift_end": shift_end.strftime(_FMT),
		"shift_hours": shift_hours,
		"worked_hours": _round2(worked),
		"total_hours": _round2(total),
		"overtime_hours": overtime,
		"percent": percent,
		"range_label": entry.get("scheduled_time") or f"{start_text}-{end_text}",
		"actual_start": actual_start.strftime(_FMT) if actual_start else None,
		"actual_end": actual_end.strftime(_FMT) if actual_end else None,
		"breaks": [
			{"start": a.strftime(_FMT), "end": b.strftime(_FMT)} for a, b in _lunch_windows(shift_start, shift_end)
		],
	}


# ---- 排班希望提醒（rosterCalendar.js buildHomePreferenceGroup / resolveHomePreferenceNotices）----

URGENT_DEADLINE_DAYS = 7


def _parse_day(value) -> date | None:
	try:
		return date.fromisoformat(str(value)[:10]) if value else None
	except ValueError:
		return None


def preference_notices(summary: dict | None, today: date) -> list[dict]:
	"""正在征集希望的每个月一行；截止 7 天内（含已过期）且未提交的算紧急。"""
	summary = summary or {}
	notices = summary.get("preference_notices")
	if not isinstance(notices, list):
		notices = [summary.get("preference_notice")]
	rows = []
	for notice in notices:
		if not notice or notice.get("status") != "Collecting" or not str(notice.get("period") or "").strip():
			continue
		done = bool(notice.get("has_preference"))
		deadline = _parse_day(notice.get("preference_deadline"))
		remaining = None if done or not deadline else (deadline - today).days
		rows.append(
			{
				"period": notice["period"],
				"year": int(notice["year"]) if notice.get("year") else None,
				"month": int(notice["month"]) if notice.get("month") else None,
				"department_category": notice.get("department_category"),
				"deadline": deadline.isoformat() if deadline else None,
				"has_preference": done,
				"remaining_days": remaining,
				"urgent": remaining is not None and remaining <= URGENT_DEADLINE_DAYS,
			}
		)
	return rows
