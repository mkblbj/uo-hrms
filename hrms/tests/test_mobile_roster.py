"""原生 App 排班页（M3）的计算规则：一周的起止、班次时间点、颜色、截止天数、合计和排序。"""

import unittest
from datetime import date, time, timedelta

from hrms.utils import mobile_roster as rules


def shift(start, end):
	return {"start": start, "end": end}


class TestWeekAndClock(unittest.TestCase):
	def test_week_bounds(self):
		self.assertEqual(rules.week_bounds(date(2026, 10, 20)), (date(2026, 10, 19), date(2026, 10, 25)))
		self.assertEqual(rules.week_bounds(date(2026, 10, 19)), (date(2026, 10, 19), date(2026, 10, 25)))
		self.assertEqual(rules.week_bounds(date(2026, 10, 25)), (date(2026, 10, 19), date(2026, 10, 25)))
		self.assertEqual(rules.week_bounds(date(2026, 10, 29)), (date(2026, 10, 26), date(2026, 11, 1)))

	def test_clock(self):
		self.assertEqual(rules.clock(time(9, 30)), "09:30")
		self.assertEqual(rules.clock(timedelta(hours=9, minutes=30)), "09:30")
		self.assertEqual(rules.clock("9:30:00"), "09:30")
		self.assertIsNone(rules.clock(None))
		self.assertIsNone(rules.clock(""))

	def test_shift_window_overnight(self):
		self.assertEqual(
			rules.shift_window(date(2026, 10, 16), "22:00", "06:00"),
			("2026-10-16 22:00:00", "2026-10-17 06:00:00"),
		)
		self.assertEqual(
			rules.shift_window(date(2026, 10, 6), "09:00", "18:00"),
			("2026-10-06 09:00:00", "2026-10-06 18:00:00"),
		)
		self.assertIsNone(rules.shift_window(date(2026, 10, 6), "09:00", None))

	def test_normalize_color(self):
		self.assertEqual(rules.normalize_color("#449cf0"), "#449CF0")
		self.assertEqual(rules.normalize_color("#B4CD29"), "#B4CD29")
		for value in ("", None, "red", "#abc", "449CF0"):
			self.assertIsNone(rules.normalize_color(value), value)


class TestDayFields(unittest.TestCase):
	def test_day_fields(self):
		holiday = rules.day_fields(
			date(2026, 11, 3), {"description": "<b>文化の日</b>", "weekly_off": 0}, None
		)
		self.assertEqual(
			holiday,
			{
				"date": "2026-11-03",
				"weekday": 2,
				"holiday_name": "文化の日",
				"is_weekly_off": False,
				"sale_event": None,
			},
		)
		sale = {"title": "SALE", "event_type": "Sale", "color": "#F59E0B"}
		sunday = rules.day_fields(date(2026, 11, 1), {"description": "日曜日", "weekly_off": 1}, sale)
		self.assertEqual(
			(sunday["weekday"], sunday["holiday_name"], sunday["is_weekly_off"]), (7, None, True)
		)
		self.assertEqual(sunday["sale_event"], sale)
		plain = rules.day_fields(date(2026, 11, 2), None, None)
		self.assertEqual((plain["holiday_name"], plain["is_weekly_off"]), (None, False))


class TestTotalsAndDeadline(unittest.TestCase):
	def test_totals(self):
		days = [{"shift": {"hours": hours}} for hours in (8, 4.5, 8.05)] + [{"shift": None}, {"shift": None}]
		self.assertEqual(rules.totals(days), {"shift_days": 3, "hours": 20.6})
		self.assertEqual(rules.totals([]), {"shift_days": 0, "hours": 0})

	def test_deadline_status(self):
		today = date(2026, 10, 20)
		self.assertEqual(rules.deadline_status(date(2026, 10, 23), today), (3, True))
		self.assertEqual(rules.deadline_status(date(2026, 10, 27), today), (7, True))
		self.assertEqual(rules.deadline_status(date(2026, 10, 28), today), (8, False))
		self.assertEqual(rules.deadline_status(date(2026, 10, 18), today), (-2, True))
		self.assertEqual(rules.deadline_status(None, today), (None, False))


class TestEmployeeSort(unittest.TestCase):
	def test_employee_sort_key(self):
		rows = [
			{"employee": "E5", "employee_name": "A", "shift": None},
			{
				"employee": "E4",
				"employee_name": "B",
				"shift": shift("2026-10-14 10:00:00", "2026-10-14 16:00:00"),
			},
			{
				"employee": "E3",
				"employee_name": "B",
				"shift": shift("2026-10-14 09:00:00", "2026-10-14 18:00:00"),
			},
			{
				"employee": "E2",
				"employee_name": "A",
				"shift": shift("2026-10-14 09:00:00", "2026-10-14 18:00:00"),
			},
			{
				"employee": "E1",
				"employee_name": "A",
				"shift": shift("2026-10-14 09:00:00", "2026-10-14 18:00:00"),
			},
			{
				"employee": "E6",
				"employee_name": "C",
				"shift": shift("2026-10-14 09:00:00", "2026-10-14 12:00:00"),
			},
		]
		ordered = [row["employee"] for row in sorted(rows, key=rules.employee_sort_key)]
		self.assertEqual(ordered, ["E6", "E1", "E2", "E3", "E4", "E5"])
