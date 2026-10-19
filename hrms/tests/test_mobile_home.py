# 原生 App 主页规则：照搬 PWA 前端 homeHeatmap.js / homeShiftProgress.js / rosterCalendar.js 的用例
import unittest
from datetime import date

from hrms.utils import mobile_home

TODAY = date(2026, 5, 14)


def cell_for(event, day, today=TODAY):
	return mobile_home.heatmap_cell(event, day, today)


class TestHeatmapCells(unittest.TestCase):
	def test_levels_from_hours(self):
		self.assertEqual(mobile_home.STANDARD_DAY_HOURS, 8)
		self.assertEqual(cell_for({"attendance": "Present", "working_hours": 2}, date(2026, 5, 11))["level"], 1)
		self.assertEqual(cell_for({"attendance": "Present", "working_hours": 6}, date(2026, 5, 12))["level"], 3)
		self.assertEqual(cell_for({"attendance": "Present", "working_hours": 10}, date(2026, 5, 13))["level"], 5)

	def test_non_attendance_days_are_level_zero(self):
		for event in ({"attendance": "Holiday"}, {"attendance": "Absent"}, {"attendance": "On Leave"}, None):
			cell = cell_for(event, date(2026, 5, 11))
			self.assertEqual(cell["level"], 0)
			self.assertFalse(cell["has_issue"])

	def test_anomaly_before_levels(self):
		cell = cell_for(
			{
				"attendance": "Present",
				"working_hours": 8,
				"anomaly": {"has_issue": True, "codes": ["missing_checkout"]},
			},
			date(2026, 5, 11),
		)
		self.assertTrue(cell["has_issue"])
		self.assertEqual(cell["level"], 0)

	def test_today_working_and_checked_out(self):
		today = date(2026, 9, 30)
		working = cell_for({"checkin_status": "working"}, today, today)
		checked_out = cell_for({"checkin_status": "checked_out"}, today, today)
		history = cell_for({"attendance": "Present", "working_hours": 8}, date(2026, 9, 29), today)
		self.assertEqual((working["level"], working["today_status"]), (1, "working"))
		self.assertEqual((checked_out["level"], checked_out["today_status"]), (1, "checked_out"))
		self.assertEqual((history["level"], history["today_status"]), (4, None))
		for cell in (working, checked_out):
			self.assertFalse(cell["has_issue"])
			self.assertTrue(cell["is_today"])

	def test_unpunched_today_and_future(self):
		today = date(2026, 9, 30)
		unpunched = cell_for({"checkin_status": "not_checked_in"}, today, today)
		self.assertEqual(unpunched["level"], 0)
		self.assertTrue(unpunched["is_today"])
		future = cell_for({"checkin_status": "working"}, date(2026, 10, 1), today)
		self.assertEqual(future["level"], 0)
		self.assertTrue(future["is_future"])

	def test_today_anomaly_is_ignored(self):
		today = date(2026, 9, 30)
		cell = cell_for({"checkin_status": "working", "anomaly": {"has_issue": True}}, today, today)
		self.assertFalse(cell["has_issue"])
		self.assertEqual(cell["level"], 1)

	def test_zero_hours_are_not_replaced_by_the_fallback(self):
		self.assertEqual(cell_for({"attendance": "Present", "working_hours": 0}, date(2026, 5, 11))["level"], 0)
		self.assertEqual(cell_for({"attendance": "Half Day"}, date(2026, 5, 11))["level"], 2)

	def test_grid_is_20_weeks_ending_this_week(self):
		today = date(2026, 10, 19)
		events = {
			"2026-10-12": {"attendance": "Present", "working_hours": 8},
			"2026-10-13": {"attendance": "Half Day"},
		}
		cells = mobile_home.heatmap_cells(events, today)
		self.assertEqual(len(cells), 140)
		self.assertEqual(mobile_home.heatmap_range(today), (date(2026, 6, 8), date(2026, 10, 25)))
		self.assertEqual((cells[0]["date"], cells[0]["weekday"]), ("2026-06-08", 1))
		self.assertEqual((cells[-1]["date"], cells[-1]["weekday"]), ("2026-10-25", 7))
		by_date = {cell["date"]: cell for cell in cells}
		self.assertEqual(by_date["2026-10-12"]["level"], 4)
		self.assertEqual(by_date["2026-10-13"]["level"], 2)
		self.assertTrue(by_date["2026-10-19"]["is_today"])
		self.assertTrue(by_date["2026-10-20"]["is_future"])

	def test_month_markers(self):
		cells = mobile_home.heatmap_cells({}, date(2026, 10, 19))
		self.assertEqual(
			mobile_home.heatmap_month_markers(cells),
			[
				{"week": 0, "month": 6},
				{"week": 4, "month": 7},
				{"week": 8, "month": 8},
				{"week": 13, "month": 9},
				{"week": 17, "month": 10},
			],
		)


SCHEDULE = {
	"date": "2026-05-19",
	"start_time": "09:00",
	"end_time": "18:00",
	"scheduled_time": "09:00-18:00",
	"hours": 8,
}


def at(text):
	from datetime import datetime

	return datetime.fromisoformat(text)


def working(since):
	return {"status": "working", "last_checkin": {"log_type": "IN", "time": since}}


class TestTodayProgress(unittest.TestCase):
	def test_no_usable_schedule(self):
		self.assertIsNone(mobile_home.today_progress(None, {}, {}, at("2026-05-19 10:00:00")))
		self.assertIsNone(mobile_home.today_progress({"date": "2026-05-19"}, {}, {}, at("2026-05-19 10:00:00")))

	def test_equal_times_are_zero_hours(self):
		entry = {"date": "2026-05-19", "start_time": "09:00", "end_time": "09:00", "scheduled_time": "09:00-09:00"}
		self.assertIsNone(mobile_home.today_progress(entry, {}, {}, at("2026-05-19 10:00:00")))

	def test_zero_until_checked_in(self):
		p = mobile_home.today_progress(SCHEDULE, {}, {"status": "no_checkin_today"}, at("2026-05-19 10:30:00"))
		self.assertEqual((p["percent"], p["status_key"], p["worked_hours"], p["shift_hours"]), (0, "pending", 0, 8))
		self.assertEqual(p["range_label"], "09:00-18:00")
		self.assertEqual((p["shift_start"], p["shift_end"]), ("2026-05-19 09:00:00", "2026-05-19 18:00:00"))
		self.assertEqual(p["breaks"], [{"start": "2026-05-19 12:00:00", "end": "2026-05-19 13:00:00"}])
		self.assertIsNone(p["actual_start"])

	def test_live_progress_from_first_checkin(self):
		p = mobile_home.today_progress(
			SCHEDULE,
			{"first_checkin_today": "2026-05-19 09:30:00"},
			working("2026-05-19 09:30:00"),
			at("2026-05-19 13:30:00"),
		)
		self.assertEqual((p["percent"], p["status_key"], p["worked_hours"]), (37.5, "working", 3.0))
		self.assertEqual((p["actual_start"], p["actual_end"]), ("2026-05-19 09:30:00", "2026-05-19 13:30:00"))

	def test_lunch_deducted_without_planned_hours(self):
		entry = {k: v for k, v in SCHEDULE.items() if k != "hours"}
		p = mobile_home.today_progress(
			entry, {"first_checkin_today": "2026-05-19 09:00:00"}, working("2026-05-19 09:00:00"), at("2026-05-19 12:30:00")
		)
		self.assertEqual((p["shift_hours"], p["worked_hours"], p["percent"]), (8, 3, 37.5))

	def test_planned_hours_win(self):
		p = mobile_home.today_progress({**SCHEDULE, "hours": 7.5}, {}, {"status": "no_checkin_today"}, at("2026-05-19 10:00:00"))
		self.assertEqual(p["shift_hours"], 7.5)

	def test_exact_lunch_boundaries(self):
		for start, end, expected in (("09:00", "12:00", 3), ("13:00", "18:00", 5), ("11:30", "12:30", 0.5)):
			entry = {"date": "2026-05-19", "start_time": start, "end_time": end, "scheduled_time": f"{start}-{end}"}
			p = mobile_home.today_progress(entry, {}, {}, at("2026-05-19 08:00:00"))
			self.assertEqual(p["shift_hours"], expected, (start, end))

	def test_completed_shift_uses_last_checkout(self):
		p = mobile_home.today_progress(
			SCHEDULE,
			{"first_checkin_today": "2026-05-19 09:05:00", "last_checkin_today": "2026-05-19 17:55:00"},
			{"status": "off_work", "last_checkin": {"log_type": "OUT", "time": "2026-05-19 17:55:00"}},
			at("2026-05-19 19:00:00"),
		)
		self.assertEqual((p["percent"], p["status_key"]), (97.92, "done"))
		self.assertAlmostEqual(p["worked_hours"], 7.83, places=2)

	def test_short_post_shift_minutes_stay_normal(self):
		p = mobile_home.today_progress(
			SCHEDULE, {"first_checkin_today": "2026-05-19 09:00:00"}, working("2026-05-19 09:00:00"), at("2026-05-19 18:29:00")
		)
		self.assertEqual((p["percent"], p["status_key"], p["overtime_hours"]), (100, "working", 0.48))

	def test_overtime_from_thirty_minutes(self):
		p = mobile_home.today_progress(
			SCHEDULE, {"first_checkin_today": "2026-05-19 09:00:00"}, working("2026-05-19 09:00:00"), at("2026-05-19 18:30:00")
		)
		self.assertEqual((p["percent"], p["status_key"], p["overtime_hours"], p["total_hours"]), (100, "overtime", 0.5, 8.5))

	def test_active_overtime(self):
		p = mobile_home.today_progress(
			SCHEDULE, {"first_checkin_today": "2026-05-19 09:00:00"}, working("2026-05-19 09:00:00"), at("2026-05-19 18:36:00")
		)
		self.assertEqual((p["status_key"], p["overtime_hours"], p["total_hours"]), ("overtime", 0.6, 8.6))

	def test_completed_overtime_stays_visible(self):
		p = mobile_home.today_progress(
			SCHEDULE,
			{"first_checkin_today": "2026-05-19 09:00:00", "last_checkin_today": "2026-05-19 18:45:00"},
			{"status": "off_work", "last_checkin": {"log_type": "OUT", "time": "2026-05-19 18:45:00"}},
			at("2026-05-19 19:00:00"),
		)
		self.assertEqual((p["percent"], p["status_key"], p["overtime_hours"], p["total_hours"]), (100, "done", 0.75, 8.75))

	def test_progress_overnight_shift(self):
		entry = {"date": "2026-05-19", "start_time": "22:00", "end_time": "06:00", "scheduled_time": "22:00-06:00"}
		p = mobile_home.today_progress(
			entry, {"first_checkin_today": "2026-05-19 22:10:00"}, working("2026-05-19 22:10:00"), at("2026-05-20 02:10:00")
		)
		self.assertEqual((p["percent"], p["worked_hours"], p["shift_hours"]), (50, 4.0, 8))
		self.assertEqual(p["shift_end"], "2026-05-20 06:00:00")
		self.assertEqual(p["breaks"], [])

	def test_next_day_lunch_in_cross_day_overtime(self):
		entry = {"date": "2026-05-19", "start_time": "22:00", "end_time": "06:00", "scheduled_time": "22:00-06:00"}
		p = mobile_home.today_progress(
			entry, {"first_checkin_today": "2026-05-19 22:00:00"}, working("2026-05-19 22:00:00"), at("2026-05-20 13:30:00")
		)
		self.assertEqual((p["shift_hours"], p["worked_hours"], p["total_hours"], p["overtime_hours"]), (8, 8, 14.5, 6.5))


def collecting(period, year, month, has_preference, deadline=None, category="Office"):
	return {
		"period": period,
		"year": year,
		"month": month,
		"department_category": category,
		"status": "Collecting",
		"preference_deadline": deadline,
		"has_preference": has_preference,
	}


class TestPreferenceNotices(unittest.TestCase):
	def test_every_collecting_month(self):
		oct_, dec = collecting("Office-2044-10", 2044, 10, False), collecting("Office-2044-12", 2044, 12, True)
		rows = mobile_home.preference_notices({"preference_notice": oct_, "preference_notices": [oct_, dec]}, date(2044, 9, 1))
		self.assertEqual([r["period"] for r in rows], ["Office-2044-10", "Office-2044-12"])

	def test_skips_not_collecting_or_without_period(self):
		oct_ = collecting("Office-2044-10", 2044, 10, False)
		summary = {
			"preference_notices": [
				oct_,
				{**oct_, "period": "Office-2044-11", "status": "Scheduling"},
				{**oct_, "period": "Office-2044-12", "status": "Published"},
				{**oct_, "period": ""},
				{"status": "Collecting", "has_preference": False},
				None,
			]
		}
		self.assertEqual([r["period"] for r in mobile_home.preference_notices(summary, date(2044, 9, 1))], ["Office-2044-10"])
		self.assertEqual(mobile_home.preference_notices(None, date(2044, 9, 1)), [])
		self.assertEqual(mobile_home.preference_notices({"preference_notices": []}, date(2044, 9, 1)), [])

	def test_single_notice_from_older_server(self):
		oct_ = collecting("Office-2044-10", 2044, 10, False)
		self.assertEqual(len(mobile_home.preference_notices({"preference_notice": oct_}, date(2044, 9, 1))), 1)
		self.assertEqual(mobile_home.preference_notices({"preference_notice": {**oct_, "status": "Scheduling"}}, date(2044, 9, 1)), [])

	def test_row_fields(self):
		row = mobile_home.preference_notices(
			{"preference_notices": [collecting("Office-2026-11", 2026, 11, False, "2026-10-20")]}, date(2026, 10, 12)
		)[0]
		self.assertEqual(
			row,
			{
				"period": "Office-2026-11",
				"year": 2026,
				"month": 11,
				"department_category": "Office",
				"deadline": "2026-10-20",
				"has_preference": False,
				"remaining_days": 8,
				"urgent": False,
			},
		)

	def test_deadline_within_a_week_is_urgent_only_when_not_submitted(self):
		rows = mobile_home.preference_notices(
			{
				"preference_notices": [
					collecting("A", 2026, 11, False, "2026-10-19"),
					collecting("B", 2026, 12, False, "2026-10-20"),
					collecting("C", 2027, 1, False, "2026-10-01"),
					collecting("D", 2027, 2, True, "2026-10-13"),
					collecting("E", 2027, 3, False),
				]
			},
			date(2026, 10, 12),
		)
		self.assertEqual([(r["remaining_days"], r["urgent"]) for r in rows], [(7, True), (8, False), (-11, True), (None, False), (None, False)])
