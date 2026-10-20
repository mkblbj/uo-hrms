from datetime import datetime
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import mobile
from hrms.hr.doctype.employee_checkin.test_employee_checkin import make_checkin
from hrms.tests.test_mobile_api import NO_EMPLOYEE_USER, ensure_user
from hrms.tests.utils import HRMSTestSuite

USER = "mobile-attendance@example.com"
OTHER_USER = "mobile-attendance-other@example.com"
APPROVER = "mobile-attendance-approver@example.com"
# 五月的数据都在真实今天之前；接口里的「今天」用 patch 固定在 5 月 25 日
NOW = datetime(2026, 5, 25, 10, 0)


def roster(day, hours=8.0, start="09:00", end="18:00", label="9-18"):
	return {"date": day, "hours": hours, "start_time": start, "end_time": end, "shift_label": label}


def submit_attendance(employee, day, status="Present", hours=8.0):
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": day,
			"status": status,
			"working_hours": hours,
			"company": "_Test Company",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc


class MobileAttendanceTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_user(APPROVER)
		self.employee = make_employee(USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for user in (USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
		frappe.db.set_value("Employee", self.employee, "attendance_correction_approver", APPROVER)
		ensure_user(NO_EMPLOYEE_USER)
		# 测试基类给公司分配了带周日的假日表；这里给员工分配一张空表，假日只由各用例自己给
		self.holiday_list = "Mobile Attendance Empty 2026"
		if not frappe.db.exists("Holiday List", self.holiday_list):
			frappe.get_doc(
				{"doctype": "Holiday List", "holiday_list_name": self.holiday_list, "from_date": "2026-01-01", "to_date": "2026-12-31"}
			).insert(ignore_permissions=True)
		frappe.db.delete("Holiday", {"parent": self.holiday_list})
		for employee in (self.employee, self.other_employee):
			assignment = frappe.get_doc(
				{
					"doctype": "Holiday List Assignment",
					"applicable_for": "Employee",
					"assigned_to": employee,
					"holiday_list": self.holiday_list,
					"from_date": "2026-01-01",
					"to_date": "2026-12-31",
				}
			).insert(ignore_permissions=True)
			if assignment.meta.is_submittable:
				assignment.submit()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def month(self, schedule=None, now=NOW, year=2026, month=5, **kwargs):
		with (
			patch.object(mobile, "_month_schedule", return_value=schedule),
			patch.object(mobile, "now_datetime", return_value=now),
		):
			return frappe.call("hrms.api.mobile.get_attendance_month", year=year, month=month, **kwargs)

	def day_of(self, result, date):
		return next(row for row in result["days"] if row["date"] == date)


class TestAttendanceMonth(MobileAttendanceTestCase):
	def test_month_shape(self):
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []}, year=2026, month=10, now=datetime(2026, 10, 20, 9))
		self.assertEqual(set(result), {"api_version", "year", "month", "today", "days", "summary"})
		self.assertEqual((result["api_version"], result["year"], result["month"]), (1, 2026, 10))
		self.assertEqual(len(result["days"]), 31)
		first = result["days"][0]
		self.assertEqual(first["date"], "2026-10-01")
		self.assertEqual(first["weekday"], 4)
		self.assertEqual(
			set(first),
			{
				"date", "weekday", "is_today", "is_future", "state", "hours", "is_half_day",
				"anomaly_codes", "has_pending_correction", "holiday_name",
			},
		)
		self.assertNotIn("_weight", first)

	def test_month_states_from_records(self):
		submit_attendance(self.employee, "2026-05-12", hours=9.6)
		submit_attendance(self.employee, "2026-05-13", status="Half Day", hours=4)
		make_checkin(self.employee, datetime(2026, 5, 14, 9, 0), log_type="IN")
		schedule = {
			"entries": [roster("2026-05-12"), roster("2026-05-13"), roster("2026-05-14"), roster("2026-05-26")],
			"holidays": [{"holiday_date": "2026-05-05", "description": "こどもの日", "weekly_off": 0}],
		}
		frappe.set_user(USER)
		result = self.month(schedule)

		overtime = self.day_of(result, "2026-05-12")
		self.assertEqual((overtime["state"], overtime["hours"], overtime["is_half_day"]), ("overtime", 9.6, False))
		half = self.day_of(result, "2026-05-13")
		self.assertEqual((half["state"], half["hours"], half["is_half_day"]), ("work", 4.0, True))
		anomaly = self.day_of(result, "2026-05-14")
		self.assertEqual((anomaly["state"], anomaly["anomaly_codes"]), ("anomaly", ["missing_checkout"]))
		holiday = self.day_of(result, "2026-05-05")
		self.assertEqual((holiday["state"], holiday["holiday_name"]), ("holiday", "こどもの日"))
		future = self.day_of(result, "2026-05-26")
		self.assertEqual((future["state"], future["is_future"], future["hours"]), ("scheduled", True, None))
		self.assertEqual(self.day_of(result, "2026-05-01")["anomaly_codes"], [])

		summary = result["summary"]
		self.assertEqual(summary["hours"], 13.6)
		self.assertEqual(summary["present_days"], 1.5)
		self.assertEqual(summary["overtime_hours"], 1.6)
		self.assertEqual(summary["leave_days"], 0.5)
		self.assertEqual(summary["issue_count"], 1)

	def test_month_weekly_off_is_rest(self):
		schedule = {"entries": [], "holidays": [{"holiday_date": "2026-05-03", "description": "Sunday", "weekly_off": 1}]}
		frappe.set_user(USER)
		day = self.day_of(self.month(schedule), "2026-05-03")
		self.assertEqual((day["state"], day["holiday_name"]), ("rest", None))

	def test_month_hrms_holiday_list(self):
		# hrms 假日表里的日子在月历底层接口里都合成成 Holiday；周休要显示成「休」
		holiday_list = frappe.get_doc("Holiday List", self.holiday_list)
		holiday_list.append("holidays", {"holiday_date": "2026-05-03", "description": "Sunday", "weekly_off": 1})
		holiday_list.append("holidays", {"holiday_date": "2026-05-04", "description": "みどりの日", "weekly_off": 0})
		holiday_list.save(ignore_permissions=True)
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []})
		self.assertEqual((self.day_of(result, "2026-05-03")["state"], self.day_of(result, "2026-05-03")["holiday_name"]), ("rest", None))
		self.assertEqual((self.day_of(result, "2026-05-04")["state"], self.day_of(result, "2026-05-04")["holiday_name"]), ("holiday", "みどりの日"))

	def test_month_pending_correction_flag(self):
		frappe.get_doc(
			{
				"doctype": "Attendance Correction Request",
				"employee": self.employee,
				"attendance_date": "2026-05-14",
				"request_type": "Forgot Check-out",
				"requested_log_type": "OUT",
				"requested_time": "2026-05-14 18:00:00",
				"reason": "forgot",
				"status": "Pending",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []})
		self.assertTrue(self.day_of(result, "2026-05-14")["has_pending_correction"])
		self.assertFalse(self.day_of(result, "2026-05-15")["has_pending_correction"])

	def test_month_summary_uses_roster(self):
		frappe.set_user(USER)
		summary = self.month({"entries": [roster("2026-05-20"), roster("2026-05-26")], "holidays": []})["summary"]
		self.assertEqual((summary["scheduled_days"], summary["remaining_days"]), (2, 1))

	def test_month_today_follows_site_clock(self):
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []}, year=2026, month=10, now=datetime(2026, 10, 20, 23, 30))
		self.assertEqual(result["today"], "2026-10-20")
		self.assertTrue(self.day_of(result, "2026-10-20")["is_today"])
		self.assertFalse(self.day_of(result, "2026-10-20")["is_future"])
		self.assertTrue(self.day_of(result, "2026-10-21")["is_future"])

	def test_month_empty(self):
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []})
		self.assertEqual({row["state"] for row in result["days"]}, {"empty"})
		self.assertEqual(
			result["summary"],
			{
				"hours": 0,
				"present_days": 0,
				"scheduled_days": 0,
				"remaining_days": 0,
				"overtime_hours": 0,
				"leave_days": 0,
				"issue_count": 0,
			},
		)

	def test_month_without_work_roster(self):
		frappe.set_user(USER)
		summary = self.month(None)["summary"]
		self.assertIsNone(summary["scheduled_days"])
		self.assertIsNone(summary["remaining_days"])

	def test_month_ignores_employee_param(self):
		submit_attendance(self.other_employee, "2026-05-12", hours=8)
		frappe.set_user(USER)
		result = self.month({"entries": [], "holidays": []}, employee=self.other_employee)
		self.assertEqual(self.day_of(result, "2026-05-12")["state"], "empty")

	def test_month_rejects_bad_month(self):
		frappe.set_user(USER)
		for month in (0, 13):
			with self.assertRaises(frappe.ValidationError):
				self.month({"entries": [], "holidays": []}, month=month)

	def test_month_requires_employee(self):
		frappe.set_user(NO_EMPLOYEE_USER)
		with self.assertRaises(frappe.PermissionError):
			self.month({"entries": [], "holidays": []})
