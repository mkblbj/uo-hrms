"""原生 App 勤怠页的计算规则。

PWA attendanceCalendarState.test.js 里仍适用的用例逐条翻译过来，另加 M2 的四条新规则：
按所定时长算加班、未来排班日、周休算「休」、每天先取一位小数再合计。
"""

import unittest
from datetime import date, datetime, timedelta

from hrms.utils import mobile_attendance as rules

TODAY = date(2026, 10, 20)
PAST = date(2026, 10, 5)
TOMORROW = date(2026, 10, 21)
ROSTER_8 = {"hours": 8.0}


def present(hours, status="Present", **extra):
	return {"attendance": status, "working_hours": hours, **extra}


def state(event=None, holiday=None, roster=None, day=PAST):
	return rules.derive_day_state(event, holiday, roster, day, TODAY)


class TestDayState(unittest.TestCase):
	def test_anomaly_outranks_everything(self):
		self.assertEqual(state(present(8, anomaly={"has_issue": True, "codes": ["missing_checkout"]}), {"weekly_off": 0}), "anomaly")
		self.assertEqual(state(present(8, anomaly={"has_issue": False})), "work")

	def test_status_maps_to_state(self):
		self.assertEqual(state(present(8)), "work")
		self.assertEqual(state(present(7, "Work From Home")), "work")
		self.assertEqual(state(present(4, "Half Day")), "work")
		self.assertEqual(state({"attendance": "On Leave"}), "leave")
		# 和 PWA 一样，缺勤先显示成休息
		self.assertEqual(state({"attendance": "Absent"}), "rest")

	def test_holiday_and_weekly_off(self):
		self.assertEqual(state({}, {"weekly_off": 0, "description": "山の日"}), "holiday")
		self.assertEqual(state({}, {"weekly_off": 1, "description": "Sunday"}), "rest")
		# 新规则 3：hrms 假日表把周休也合成成 Holiday，要按 weekly_off 显示成「休」
		self.assertEqual(state({"attendance": "Holiday"}, {"weekly_off": 1}), "rest")
		self.assertEqual(state({"attendance": "Holiday"}, None), "holiday")

	def test_empty_without_records(self):
		self.assertEqual(state({}), "empty")
		self.assertEqual(state(None), "empty")

	def test_today_status_before_settlement(self):
		self.assertEqual(state({"checkin_status": "working"}, day=TODAY), "working")
		self.assertEqual(state({"checkin_status": "checked_out"}, day=TODAY), "checked_out")
		holiday = {"weekly_off": 0, "description": "祝日"}
		self.assertEqual(state({"checkin_status": "working", "attendance": "Holiday"}, holiday, day=TODAY), "working")

	def test_future_rostered_day_is_scheduled(self):
		self.assertEqual(state({}, roster=ROSTER_8, day=TOMORROW), "scheduled")
		self.assertEqual(state({"checkin_status": "not_checked_in"}, roster=ROSTER_8, day=TODAY), "scheduled")
		self.assertEqual(state({}, day=TOMORROW), "empty")
		self.assertEqual(state({}, {"weekly_off": 0, "description": "文化の日"}, ROSTER_8, TOMORROW), "scheduled")
		# 过去有排班但没有记录：不是 scheduled
		self.assertEqual(state({}, roster=ROSTER_8, day=PAST), "empty")

	def test_overtime_against_scheduled_hours(self):
		self.assertEqual(state(present(8.4), roster=ROSTER_8), "work")
		self.assertEqual(rules.day_overtime(8.4, 8), 0.4)
		self.assertEqual(state(present(8.5), roster=ROSTER_8), "overtime")
		self.assertEqual(rules.day_overtime(8.5, 8), 0.5)
		self.assertEqual(state(present(7), roster={"hours": 6}), "overtime")
		self.assertEqual(rules.day_overtime(7, 6), 1.0)
		self.assertEqual(rules.day_overtime(9.6, None), 1.6)
		self.assertEqual(rules.day_overtime(None, 8), 0)
		self.assertEqual(rules.day_overtime(6, 8), 0)


class TestDayNumbers(unittest.TestCase):
	def test_hours_round_to_one_decimal(self):
		self.assertEqual(rules.day_hours(present(8.46)), 8.5)
		self.assertEqual(rules.day_hours(present(8.44)), 8.4)
		self.assertEqual(rules.day_hours(present(8.25)), 8.3)
		self.assertIsNone(rules.day_hours(present(0)))
		self.assertIsNone(rules.day_hours({"attendance": "Holiday"}))
		self.assertIsNone(rules.day_hours({"checkin_status": "working"}))
		self.assertIsNone(rules.day_hours(None))

	def test_weights(self):
		self.assertEqual([rules.day_weight(present(8, s)) for s in ("Present", "Work From Home", "Half Day", "On Leave", "Absent")], [1, 1, 0.5, 0, 0])
		self.assertEqual([rules.leave_weight(present(8, s)) for s in ("Present", "Half Day", "On Leave")], [0, 0.5, 1])
		self.assertEqual(rules.day_weight(None), 0)


def day(state, hours=None, weight=0, leave=0, overtime=0, raw=None):
	return {
		"state": state,
		"hours": hours,
		"_raw_hours": hours if raw is None else raw,
		"_weight": weight,
		"_leave": leave,
		"_overtime": overtime,
	}


class TestSummary(unittest.TestCase):
	def test_summary_counts_only_settled_work(self):
		days = [
			day("work", 8.0, 1),
			day("overtime", 9.6, 1, overtime=1.6),
			day("work", 4.0, 0.5, leave=0.5),
			day("working", 4.0),
			day("checked_out", 6.0),
			day("anomaly", 3.0, 1),
			day("leave", leave=1),
			day("rest"),
		]
		self.assertEqual(
			rules.summarize_month(days, 21, 9),
			{
				"hours": 21.6,
				"present_days": 2.5,
				"scheduled_days": 21,
				"remaining_days": 9,
				"overtime_hours": 1.6,
				"leave_days": 1.5,
				"issue_count": 1,
			},
		)

	def test_summary_sums_unrounded_hours(self):
		# 每天的格子显示 2.0，但月度合计用原始工时相加再取一次（和主页的「本月実働」一致）
		days = [day("work", rules.day_hours(present(2.04)), 1, raw=rules.raw_day_hours(present(2.04))) for _ in range(3)]
		self.assertEqual([row["hours"] for row in days], [2.0, 2.0, 2.0])
		self.assertEqual(rules.summarize_month(days, None, None)["hours"], 6.1)

	def test_summary_matches_home_total_on_dev_data(self):
		# 2026-10-20 开发站点 ios-dev 的 10 月：主页 99.79（显示 99.8），按天取整再加是 100.1
		raw = [8.17, 8.17, 8.17, 9.88, 8.15, 8.17, 8.38, 8.17, 8.07, 8.17, 8.12, 8.17]
		days = [day("work", rules.day_hours(present(hours)), 1, raw=rules.raw_day_hours(present(hours))) for hours in raw]
		self.assertEqual(rules.summarize_month(days, None, None)["hours"], 99.8)

	def test_raw_day_hours(self):
		self.assertEqual(rules.raw_day_hours(present(8.17)), 8.17)
		self.assertIsNone(rules.raw_day_hours(present(0)))
		self.assertIsNone(rules.raw_day_hours({"attendance": "Holiday", "working_hours": 8}))
		self.assertIsNone(rules.raw_day_hours(None))

	def test_summary_empty(self):
		self.assertEqual(
			rules.summarize_month([], None, None),
			{
				"hours": 0,
				"present_days": 0,
				"scheduled_days": None,
				"remaining_days": None,
				"overtime_hours": 0,
				"leave_days": 0,
				"issue_count": 0,
			},
		)


class TestDayDetailRules(unittest.TestCase):
	def test_shift_window_overnight(self):
		self.assertEqual(
			rules.shift_window({"start_time": "22:00", "end_time": "06:00", "hours": 7.0, "shift_label": "22-6"}, TODAY),
			{"start": "2026-10-20 22:00:00", "end": "2026-10-21 06:00:00", "slot": "22-6", "hours": 7.0},
		)
		self.assertEqual(
			rules.shift_window({"start_time": "09:00", "end_time": "18:00", "hours": 8, "shift_label": "9-18"}, TODAY),
			{"start": "2026-10-20 09:00:00", "end": "2026-10-20 18:00:00", "slot": "9-18", "hours": 8.0},
		)

	def test_shift_window_from_scheduled_time(self):
		# work_roster get_my_schedule 的条目只有 scheduled_time，没有 start_time / end_time
		self.assertEqual(
			rules.shift_window({"scheduled_time": "22:00-06:00", "hours": 7.0, "shift_label": "22-6"}, TODAY),
			{"start": "2026-10-20 22:00:00", "end": "2026-10-21 06:00:00", "slot": "22-6", "hours": 7.0},
		)

	def test_shift_window_missing_time(self):
		self.assertIsNone(rules.shift_window(None, TODAY))
		self.assertIsNone(rules.shift_window({"start_time": "09:00", "end_time": None, "hours": 8}, TODAY))

	def test_punch_method_and_evidence(self):
		self.assertEqual(
			[rules.punch_method(m) for m in ("QR", "Passkey", "Attendance Correction", None, "Biometric")],
			["qr", "passkey", "correction", "other", "other"],
		)
		self.assertEqual(rules.punch_evidence("passkey", None, None), "office_network")
		self.assertEqual(rules.punch_evidence("passkey", 35.68, 139.76), "gps")
		# 扫码带了定位也不一定核对过距离（只在开了地理位置追踪且不在公司网络时才核对），不推断
		self.assertIsNone(rules.punch_evidence("qr", 35.68, 139.76))
		self.assertIsNone(rules.punch_evidence("qr", None, None))
		self.assertIsNone(rules.punch_evidence("correction", 35.68, 139.76))
		self.assertIsNone(rules.punch_evidence("other", 0, 0))

	def test_stored_evidence_wins(self):
		self.assertEqual(rules.punch_evidence("device_key", None, None, stored="beacon"), "beacon")
		self.assertEqual(rules.punch_evidence("qr", 35.6, 139.7, stored="qr"), "qr")

	def test_old_records_are_still_inferred(self):
		self.assertEqual(rules.punch_evidence("passkey", None, None, stored=None), "office_network")
		self.assertEqual(rules.punch_evidence("passkey", 35.68, 139.76, stored=None), "gps")
		self.assertIsNone(rules.punch_evidence("qr", 35.68, 139.76, stored=None))

	def test_lunch_segments(self):
		def period(start, end):
			return {"counted_in_time": datetime(2026, 10, 20, *start), "counted_out_time": datetime(2026, 10, 20, *end)}

		self.assertEqual(
			rules.lunch_segments([period((9, 0), (18, 0))], "12:00:00", "13:00:00"),
			[{"start": "2026-10-20 12:00:00", "end": "2026-10-20 13:00:00"}],
		)
		self.assertEqual(
			rules.lunch_segments([period((11, 30), (12, 30))], timedelta(hours=12), timedelta(hours=13)),
			[{"start": "2026-10-20 12:00:00", "end": "2026-10-20 12:30:00"}],
		)
		self.assertEqual(rules.lunch_segments([period((9, 0), (11, 0))], "12:00:00", "13:00:00"), [])
		self.assertEqual(rules.lunch_segments([period((9, 0), (18, 0))], None, None), [])
