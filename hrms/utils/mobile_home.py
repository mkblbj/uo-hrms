"""原生 App 主页的计算规则（从 PWA 前端搬来，PWA 的 node:test 用例是规格）。

只做纯计算，不读数据库；数据由 hrms.api.mobile 取好再传进来。
"""

from datetime import date, timedelta

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
