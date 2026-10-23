import frappe
from frappe.utils import add_days

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import get_attendance_calendar_events
from hrms.tests.utils import HRMSTestSuite

OWNER_USER = "calendar-owner@example.com"
OTHER_USER = "calendar-other@example.com"
FROM_DATE = "2026-09-01"
TO_DATE = "2026-09-30"


class TestAttendanceCalendarAccess(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.owner = make_employee(OWNER_USER, company="_Test Company")
		self.other = make_employee(OTHER_USER, company="_Test Company")
		frappe.set_user(OWNER_USER)

	def tearDown(self):
		frappe.set_user("Administrator")
		# 回滚这条用例的改动：测试跑完 Frappe 会提交一次，不回滚的话 HR 设置等会留在共用的开发站点上
		super().tearDown()

	def test_employee_can_view_own_calendar(self):
		self.assertIsInstance(get_attendance_calendar_events(FROM_DATE, TO_DATE), dict)
		self.assertIsInstance(get_attendance_calendar_events(FROM_DATE, TO_DATE, employee=self.owner), dict)

	def test_employee_cannot_view_another_employees_calendar(self):
		with self.assertRaises(frappe.PermissionError):
			get_attendance_calendar_events(FROM_DATE, TO_DATE, employee=self.other)

	def test_hr_manager_cannot_view_another_employees_calendar(self):
		frappe.set_user("Administrator")
		frappe.get_doc("User", OWNER_USER).add_roles("HR Manager")
		frappe.set_user(OWNER_USER)

		with self.assertRaises(frappe.PermissionError):
			get_attendance_calendar_events(FROM_DATE, TO_DATE, employee=self.other)

	def test_accepts_range_of_400_days(self):
		to_date = str(add_days(FROM_DATE, 399))
		self.assertIsInstance(get_attendance_calendar_events(FROM_DATE, to_date), dict)

	def test_rejects_range_longer_than_400_days(self):
		to_date = str(add_days(FROM_DATE, 400))
		with self.assertRaises(frappe.ValidationError):
			get_attendance_calendar_events(FROM_DATE, to_date)
