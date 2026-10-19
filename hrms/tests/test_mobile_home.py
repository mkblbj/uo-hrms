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
