from datetime import datetime
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import mobile
from hrms.tests.test_mobile_api import NO_EMPLOYEE_USER, ensure_user
from hrms.tests.utils import HRMSTestSuite

USER = "mobile-roster@example.com"
OTHER_USER = "mobile-roster-other@example.com"
THIRD_USER = "mobile-roster-third@example.com"
PROD_USER = "mobile-roster-prod@example.com"
COMPANY = "_Test Company"
# 用 2031 年：开发站点上没有这一年的排班、大促和「Japan Holidays 2031」
YEAR = 2031
HOLIDAY_LIST = "Mobile Roster Holidays 2031"
NOW = datetime(2031, 10, 20, 10, 0)  # 周一


def ensure_department(name, category):
	full_name = f"{name} - _TC"
	if not frappe.db.exists("Department", full_name):
		frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": name,
				"company": COMPANY,
				"parent_department": "All Departments",
			}
		).insert(ignore_permissions=True)
	frappe.db.set_value("Department", full_name, "department_category", category)
	return full_name


def ensure_slot(name, start, end, category="Both", color=None, active=1):
	doc = (
		frappe.get_doc("WR Shift Slot", name)
		if frappe.db.exists("WR Shift Slot", name)
		else frappe.new_doc("WR Shift Slot")
	)
	doc.update(
		{
			"slot_name": name,
			"start_time": start,
			"end_time": end,
			"department_category": category,
			"color": color,
			"is_active": active,
		}
	)
	doc.save(ignore_permissions=True)


def ensure_period(category, month, status, deadline=None):
	name = f"{category}-{YEAR}-{month:02d}"
	doc = (
		frappe.get_doc("WR Period", name)
		if frappe.db.exists("WR Period", name)
		else frappe.new_doc("WR Period")
	)
	doc.update(
		{
			"year": YEAR,
			"month": month,
			"department_category": category,
			"status": status,
			"company": COMPANY,
			"holiday_list": HOLIDAY_LIST,
			"preference_deadline": deadline,
		}
	)
	doc.save(ignore_permissions=True)
	return doc.name


class MobileRosterTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_user(NO_EMPLOYEE_USER)
		self.office = ensure_department("Mobile Roster Office", "Office")
		self.production = ensure_department("Mobile Roster Production", "Production")
		self.employees = {}
		for user, name, department in (
			(USER, "Roster C", self.office),
			(OTHER_USER, "Roster B", self.office),
			(THIRD_USER, "Roster A", self.office),
			(PROD_USER, "Roster P", self.production),
		):
			employee = make_employee(user, company=COMPANY)
			frappe.db.set_value(
				"Employee", employee, {"employee_name": name, "department": department, "status": "Active"}
			)
			frappe.get_doc("User", user).add_roles("Employee")
			self.employees[user] = employee
		self.employee = self.employees[USER]

		if not frappe.db.exists("Holiday List", HOLIDAY_LIST):
			holiday_list = frappe.get_doc(
				{
					"doctype": "Holiday List",
					"holiday_list_name": HOLIDAY_LIST,
					"from_date": f"{YEAR}-01-01",
					"to_date": f"{YEAR}-12-31",
					"weekly_off": "Sunday",
				}
			)
			holiday_list.get_weekly_off_dates()
			holiday_list.append(
				"holidays", {"holiday_date": f"{YEAR}-10-13", "description": "スポーツの日", "weekly_off": 0}
			)
			holiday_list.insert(ignore_permissions=True)

		ensure_slot("mr-9-18", "09:00:00", "18:00:00", color="#449cf0")
		ensure_slot("mr-22-6", "22:00:00", "06:00:00")
		ensure_slot("mr-10-16", "10:00:00", "16:00:00", color="#ED6396")
		ensure_slot("mr-6-15", "06:00:00", "15:00:00", category="Production", color="#8FAF14")
		ensure_slot("mr-8-17", "08:00:00", "17:00:00", color="#999999", active=0)

		self.office_oct = ensure_period("Office", 10, "Published")
		self.production_oct = ensure_period("Production", 10, "Published")
		self.office_nov = ensure_period("Office", 11, "Collecting", deadline=f"{YEAR}-10-23")
		self.production_nov = ensure_period("Production", 11, "Collecting", deadline=f"{YEAR}-10-23")

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def entry(self, user, period, day, slot=None, custom=None):
		values = (
			{"wr_shift_slot": slot}
			if slot
			else {"is_custom": 1, "custom_start_time": custom[0], "custom_end_time": custom[1]}
		)
		# 这里不需要排班模块的班次变更提醒
		with patch("work_roster.shift_reminders.on_schedule_entry_change"):
			return frappe.get_doc(
				{
					"doctype": "WR Schedule Entry",
					"employee": self.employees[user],
					"wr_period": period,
					"date": day,
					"status": "Scheduled",
					**values,
				}
			).insert(ignore_permissions=True)

	def event(self, day, title, event_type="Sale", category="Both"):
		frappe.get_doc(
			{
				"doctype": "WR Calendar Event",
				"event_date": day,
				"title": title,
				"event_type": event_type,
				"department_category": category,
			}
		).insert(ignore_permissions=True)

	def call(self, method, user=USER, now=NOW, **kwargs):
		frappe.set_user(user)
		try:
			with patch.object(mobile, "now_datetime", return_value=now):
				return frappe.call(f"hrms.api.mobile.{method}", **kwargs)
		finally:
			frappe.set_user("Administrator")

	def my_roster(self, month=10, **kwargs):
		return self.call("get_my_roster", year=YEAR, month=month, **kwargs)

	def day_of(self, days, day):
		return next(row for row in days if row["date"] == day)


class TestMyRoster(MobileRosterTestCase):
	def test_my_roster_shape(self):
		result = self.my_roster()
		self.assertEqual(
			set(result),
			{
				"api_version",
				"year",
				"month",
				"today",
				"department_category",
				"published",
				"days",
				"summary",
				"week",
				"preference_notices",
			},
		)
		self.assertEqual(len(result["days"]), 31)
		first = result["days"][0]
		self.assertEqual(
			set(first),
			{
				"date",
				"weekday",
				"holiday_name",
				"is_weekly_off",
				"sale_event",
				"is_today",
				"is_future",
				"shift",
			},
		)
		self.assertEqual((first["date"], first["weekday"]), ("2031-10-01", 3))
		self.assertEqual(
			(result["department_category"], result["published"], result["today"]),
			("Office", True, "2031-10-20"),
		)
		self.assertEqual(set(result["week"]), {"start", "end", "days", "shift_days", "hours"})

	def test_my_roster_shift_variants(self):
		self.entry(USER, self.office_oct, "2031-10-06", slot="mr-9-18")
		self.entry(USER, self.office_oct, "2031-10-08", custom=("09:30:00", "15:00:00"))
		self.entry(USER, self.office_oct, "2031-10-16", slot="mr-22-6")
		result = self.my_roster()
		self.assertEqual(
			self.day_of(result["days"], "2031-10-06")["shift"],
			{
				"slot": "mr-9-18",
				"start": "2031-10-06 09:00:00",
				"end": "2031-10-06 18:00:00",
				"hours": 8.0,
				"color": "#449CF0",
				"is_custom": False,
			},
		)
		custom = self.day_of(result["days"], "2031-10-08")["shift"]
		self.assertEqual(
			(custom["slot"], custom["color"], custom["is_custom"], custom["hours"]), (None, None, True, 4.5)
		)
		self.assertEqual((custom["start"], custom["end"]), ("2031-10-08 09:30:00", "2031-10-08 15:00:00"))
		overnight = self.day_of(result["days"], "2031-10-16")["shift"]
		self.assertEqual(
			(overnight["end"], overnight["color"], overnight["hours"]), ("2031-10-17 06:00:00", None, 8.0)
		)
		self.assertIsNone(self.day_of(result["days"], "2031-10-07")["shift"])
		self.assertEqual(result["summary"], {"shift_days": 3, "hours": 20.5})

	def test_my_roster_hours_fallback(self):
		entry = self.entry(USER, self.office_oct, "2031-10-06", slot="mr-9-18")
		frappe.db.set_value("WR Schedule Entry", entry.name, "hours", 0)
		self.assertEqual(self.day_of(self.my_roster()["days"], "2031-10-06")["shift"]["hours"], 8.0)

	def test_my_roster_only_mine_and_published(self):
		self.entry(OTHER_USER, self.office_oct, "2031-10-07", slot="mr-9-18")
		self.entry(USER, self.office_nov, "2031-11-04", slot="mr-9-18")
		october = self.my_roster()
		self.assertIsNone(self.day_of(october["days"], "2031-10-07")["shift"])
		november = self.my_roster(month=11)
		self.assertFalse(november["published"])
		self.assertTrue(all(row["shift"] is None for row in november["days"]))
		self.assertEqual(november["summary"], {"shift_days": 0, "hours": 0})

	def test_my_roster_days_and_sales(self):
		self.event("2031-10-22", "Sale A")
		self.event("2031-10-22", "Big", event_type="Major Sale")
		self.event("2031-10-14", "Factory", category="Production")
		days = self.my_roster()["days"]
		holiday = self.day_of(days, "2031-10-13")
		self.assertEqual((holiday["holiday_name"], holiday["is_weekly_off"]), ("スポーツの日", False))
		sunday = self.day_of(days, "2031-10-19")
		self.assertEqual((sunday["holiday_name"], sunday["is_weekly_off"]), (None, True))
		today = self.day_of(days, "2031-10-20")
		self.assertEqual((today["is_today"], today["is_future"]), (True, False))
		tomorrow = self.day_of(days, "2031-10-21")
		self.assertEqual((tomorrow["is_today"], tomorrow["is_future"]), (False, True))
		self.assertEqual(self.day_of(days, "2031-10-22")["sale_event"]["event_type"], "Major Sale")
		self.assertIsNone(self.day_of(days, "2031-10-14")["sale_event"])

	def test_week_spans_months(self):
		self.entry(USER, self.office_oct, "2031-10-27", slot="mr-9-18")
		self.entry(USER, self.office_oct, "2031-10-28", slot="mr-10-16")
		self.entry(USER, self.office_nov, "2031-11-01", slot="mr-9-18")
		week = self.my_roster(month=8, now=datetime(2031, 10, 30, 9, 0))["week"]
		self.assertEqual((week["start"], week["end"], len(week["days"])), ("2031-10-27", "2031-11-02", 7))
		self.assertIsNone(self.day_of(week["days"], "2031-11-01")["shift"])
		self.assertEqual((week["shift_days"], week["hours"]), (2, 13.0))
		self.assertTrue(self.day_of(week["days"], "2031-10-30")["is_today"])

	def test_my_roster_preference_notices(self):
		notices = self.my_roster()["preference_notices"]
		notice = next(row for row in notices if row["period"] == self.office_nov)
		self.assertEqual(
			(notice["remaining_days"], notice["urgent"], notice["has_preference"]), (3, True, False)
		)
		self.assertNotIn(self.production_nov, [row["period"] for row in notices])

	def test_my_roster_department_defaults_office(self):
		frappe.db.set_value("Employee", self.employee, "department", None)
		self.entry(USER, self.office_oct, "2031-10-06", slot="mr-9-18")
		result = self.my_roster()
		self.assertEqual(result["department_category"], "Office")
		self.assertIsNotNone(self.day_of(result["days"], "2031-10-06")["shift"])

	def test_my_roster_rejects_bad_params(self):
		for year, month in ((YEAR, 13), (YEAR, 0), (1999, 10)):
			with self.assertRaises(frappe.ValidationError):
				self.call("get_my_roster", year=year, month=month)

	def test_my_roster_requires_employee(self):
		with self.assertRaises(frappe.PermissionError):
			self.my_roster(user=NO_EMPLOYEE_USER)


class TestDepartmentRoster(MobileRosterTestCase):
	def department(self, date="2031-10-15", user=USER, **kwargs):
		return self.call("get_department_roster", user=user, date=date, **kwargs)

	def test_department_week_shape(self):
		result = self.department()
		self.assertEqual(
			set(result),
			{
				"api_version",
				"today",
				"department_category",
				"my_department_category",
				"week_start",
				"week_end",
				"days",
			},
		)
		self.assertEqual(
			(result["week_start"], result["week_end"], len(result["days"])), ("2031-10-13", "2031-10-19", 7)
		)
		self.assertEqual(
			(result["department_category"], result["my_department_category"]), ("Office", "Office")
		)
		self.assertEqual(
			set(result["days"][0]),
			{
				"date",
				"weekday",
				"holiday_name",
				"is_weekly_off",
				"sale_event",
				"is_today",
				"published",
				"headcount",
				"equivalent_headcount",
				"employees",
			},
		)

	def test_department_employees_sorted(self):
		self.entry(USER, self.office_oct, "2031-10-14", slot="mr-10-16")
		self.entry(OTHER_USER, self.office_oct, "2031-10-14", slot="mr-9-18")
		self.entry(THIRD_USER, self.office_oct, "2031-10-14", slot="mr-9-18")
		employees = self.day_of(self.department()["days"], "2031-10-14")["employees"]
		self.assertEqual([row["employee_name"] for row in employees], ["Roster A", "Roster B", "Roster C"])
		self.assertEqual([row["is_me"] for row in employees], [False, False, True])
		self.assertEqual(set(employees[0]), {"employee", "employee_name", "is_me", "shift"})
		self.assertEqual(employees[2]["shift"]["slot"], "mr-10-16")

	def test_department_office_headcount(self):
		for user in (USER, OTHER_USER, THIRD_USER):
			self.entry(user, self.office_oct, "2031-10-14", slot="mr-9-18")
		days = self.department()["days"]
		busy = self.day_of(days, "2031-10-14")
		self.assertEqual((busy["headcount"], busy["equivalent_headcount"]), (3, None))
		empty = self.day_of(days, "2031-10-15")
		self.assertEqual(
			(empty["headcount"], empty["employees"], empty["equivalent_headcount"]), (0, [], None)
		)

	def test_department_production_equivalent(self):
		self.entry(PROD_USER, self.production_oct, "2031-10-14", slot="mr-6-15")
		self.entry(OTHER_USER, self.production_oct, "2031-10-14", slot="mr-9-18")
		self.entry(THIRD_USER, self.production_oct, "2031-10-14", slot="mr-10-16")
		result = self.department(department_category="Production")
		self.assertEqual(
			(result["department_category"], result["my_department_category"]), ("Production", "Office")
		)
		day = self.day_of(result["days"], "2031-10-14")
		self.assertEqual((day["headcount"], day["equivalent_headcount"]), (3, 2.6))
		self.assertEqual(self.day_of(result["days"], "2031-10-15")["equivalent_headcount"], 0.0)
		self.assertEqual(self.department(user=PROD_USER)["department_category"], "Production")

	def test_department_published_per_day(self):
		days = self.department(date="2031-10-29")["days"]
		self.assertEqual([row["published"] for row in days], [True] * 5 + [False] * 2)

	def test_department_sales_follow_category(self):
		self.event("2031-10-14", "Factory", category="Production")
		self.assertIsNone(self.day_of(self.department()["days"], "2031-10-14")["sale_event"])
		production = self.department(department_category="Production")
		self.assertEqual(self.day_of(production["days"], "2031-10-14")["sale_event"]["title"], "Factory")

	def test_department_rejects_bad_params(self):
		for kwargs in ({"department_category": "Both"}, {"date": "2031-02-30"}, {"date": ""}):
			with self.assertRaises(frappe.ValidationError, msg=str(kwargs)):
				self.department(**{"date": "2031-10-15", **kwargs})

	def test_department_requires_employee(self):
		with self.assertRaises(frappe.PermissionError):
			self.department(user=NO_EMPLOYEE_USER)


class TestPreferenceForm(MobileRosterTestCase):
	def form(self, period, user=USER):
		return self.call("get_preference_form", user=user, period=period)

	def preference(self, user, period, details, notes=None):
		return frappe.get_doc(
			{
				"doctype": "WR Preference",
				"employee": self.employees[user],
				"wr_period": period,
				"notes": notes,
				"submitted_at": "2031-10-18 21:14:00.123456",
				"details": details,
			}
		).insert(ignore_permissions=True)

	def test_form_collecting_without_preference(self):
		result = self.form(self.office_nov)
		self.assertEqual(
			set(result), {"api_version", "today", "period", "slots", "days", "lunch_break", "preference"}
		)
		self.assertEqual(
			result["period"],
			{
				"name": self.office_nov,
				"year": YEAR,
				"month": 11,
				"department_category": "Office",
				"status": "Collecting",
				"editable": True,
				"deadline": "2031-10-23",
				"remaining_days": 3,
				"urgent": True,
				"auto_schedule_notice": False,
			},
		)
		self.assertIsNone(result["preference"])
		slots = [row for row in result["slots"] if row["name"].startswith("mr-")]
		self.assertEqual([row["name"] for row in slots], ["mr-9-18", "mr-10-16", "mr-22-6"])
		self.assertEqual(
			slots[0],
			{"name": "mr-9-18", "start_time": "09:00", "end_time": "18:00", "hours": 8.0, "color": "#449CF0"},
		)
		self.assertEqual((slots[1]["hours"], slots[2]["color"]), (5.0, None))
		self.assertEqual(len(result["days"]), 30)
		self.assertEqual(
			set(result["days"][0]), {"date", "weekday", "holiday_name", "is_weekly_off", "sale_event"}
		)
		self.assertTrue(self.day_of(result["days"], "2031-11-02")["is_weekly_off"])
		self.assertEqual(result["lunch_break"], {"start": "12:00", "end": "13:00"})

	def test_form_submitted_preference(self):
		self.preference(
			USER,
			self.office_nov,
			[
				{
					"date": "2031-11-05",
					"is_custom": 1,
					"custom_start_time": "09:30:00",
					"custom_end_time": "15:00:00",
				},
				{"date": "2031-11-03", "wr_shift_slot": "mr-9-18"},
			],
			notes="午前のみ",
		)
		result = self.form(self.office_nov)
		self.assertEqual(result["period"]["remaining_days"], 3)
		self.assertEqual(
			result["preference"],
			{
				"submitted_at": "2031-10-18 21:14:00",
				"notes": "午前のみ",
				"details": [
					{
						"date": "2031-11-03",
						"wr_shift_slot": "mr-9-18",
						"custom_start_time": None,
						"custom_end_time": None,
						"is_custom": False,
					},
					{
						"date": "2031-11-05",
						"wr_shift_slot": None,
						"custom_start_time": "09:30",
						"custom_end_time": "15:00",
						"is_custom": True,
					},
				],
			},
		)

	def test_form_closed_period(self):
		# 希望只能在征集中提交：先把期改成征集中插入，再改回已发布
		frappe.db.set_value("WR Period", self.office_oct, "status", "Collecting")
		self.preference(USER, self.office_oct, [{"date": "2031-10-06", "wr_shift_slot": "mr-9-18"}])
		frappe.db.set_value(
			"WR Period", self.office_oct, {"status": "Published", "preference_deadline": f"{YEAR}-09-20"}
		)
		result = self.form(self.office_oct)
		period = result["period"]
		self.assertEqual(
			(period["status"], period["editable"], period["remaining_days"], period["urgent"]),
			("Published", False, -30, True),
		)
		self.assertEqual(result["preference"]["notes"], "")
		self.assertEqual(len(result["preference"]["details"]), 1)

	def test_form_no_deadline(self):
		frappe.db.set_value("WR Period", self.office_nov, "preference_deadline", None)
		period = self.form(self.office_nov)["period"]
		self.assertEqual(
			(period["deadline"], period["remaining_days"], period["urgent"]), (None, None, False)
		)

	def test_form_production_period(self):
		result = self.form(self.production_nov, user=PROD_USER)
		self.assertTrue(result["period"]["auto_schedule_notice"])
		self.assertIn("mr-6-15", [row["name"] for row in result["slots"]])

	def test_form_rejects_unavailable_periods(self):
		draft = ensure_period("Office", 12, "Draft")
		for period in ("Office-2031-99", draft, self.production_nov, ""):
			try:
				self.form(period)
			except frappe.PermissionError:
				self.fail(f"{period}: 不能用 403，App 收到 403 会回登录页")
			except frappe.ValidationError:
				continue
			self.fail(f"{period}: 应当 417")

	def test_form_requires_employee(self):
		with self.assertRaises(frappe.PermissionError):
			self.form(self.office_nov, user=NO_EMPLOYEE_USER)


class TestRosterReadOnly(MobileRosterTestCase):
	def test_reads_do_not_write(self):
		with patch.object(frappe.local.db, "commit") as commit:
			self.my_roster(month=8)
			self.call("get_department_roster", date="2031-08-06")
			frappe.db.set_value("WR Period", self.office_nov, "holiday_list", None)
			self.call("get_preference_form", period=self.office_nov)
		commit.assert_not_called()
		self.assertFalse(frappe.db.exists("Holiday List", "Japan Holidays 2031"))

	def test_get_only(self):
		for fn in (mobile.get_my_roster, mobile.get_department_roster, mobile.get_preference_form):
			methods = frappe.allowed_http_methods_for_whitelisted_func[fn]
			self.assertIn("GET", methods, fn.__name__)
			self.assertNotIn("POST", methods, fn.__name__)
