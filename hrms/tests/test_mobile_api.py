from unittest.mock import patch

import frappe
from frappe.utils import get_system_timezone
from frappe.utils.password import set_encrypted_password

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import mobile
from hrms.tests.test_passkey_api import ensure_location
from hrms.tests.utils import HRMSTestSuite

# 公开的测试向量密钥，不是任何真实密钥
BEACON_TEST_KEY = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
USER = "mobile-api@example.com"
OTHER_USER = "mobile-api-other@example.com"
NO_EMPLOYEE_USER = "mobile-api-no-employee@example.com"


def ensure_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Mobile", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	frappe.get_doc("User", email).add_roles("Employee")


class MobileApiTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee(USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for user in (USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
		ensure_user(NO_EMPLOYEE_USER)
		self.location = ensure_location()
		settings = frappe.get_doc("HR Settings")
		settings.passkey_checkin_location = self.location
		settings.passkey_checkin_enabled_for_all = 0
		settings.set("passkey_checkin_pilot_employees", [{"employee": self.employee}])
		settings.allow_geolocation_tracking = 1
		settings.save()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()


class TestBoot(MobileApiTestCase):
	def test_boot_for_employee(self):
		frappe.set_user(USER)
		boot = mobile.get_boot()
		self.assertEqual(boot["api_version"], 1)
		self.assertEqual(boot["timezone"], get_system_timezone())
		self.assertRegex(boot["server_time"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
		self.assertEqual(boot["user"]["name"], USER)
		self.assertEqual(boot["employee"]["name"], self.employee)
		self.assertEqual(
			set(boot["employee"]),
			{"name", "employee_name", "first_name", "department", "designation", "company", "reports_to_name"},
		)
		self.assertEqual(
			set(boot["features"]),
			{
				"mobile_checkin",
				"passkey_checkin",
				"geolocation_required",
				"profile_collection",
				"ble_checkin",
			},
		)
		self.assertTrue(boot["features"]["geolocation_required"])
		self.assertIsInstance(boot["unread_notifications"], int)

	def test_boot_without_employee(self):
		frappe.set_user(NO_EMPLOYEE_USER)
		boot = mobile.get_boot()
		self.assertIsNone(boot["employee"])
		self.assertIsNone(boot["checkin_location"])
		self.assertEqual(set(boot["features"].values()), {False})

	def test_boot_rejects_guest(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			mobile.get_boot()

	def test_boot_passkey_feature_follows_pilot(self):
		frappe.set_user(USER)
		boot = mobile.get_boot()
		self.assertTrue(boot["features"]["passkey_checkin"])
		self.assertEqual(boot["checkin_location"]["name"], self.location)
		frappe.set_user(OTHER_USER)
		boot = mobile.get_boot()
		self.assertFalse(boot["features"]["passkey_checkin"])
		self.assertIsNone(boot["checkin_location"])

	def test_boot_ble_feature_follows_switch_and_pilot(self):
		set_encrypted_password("QR Checkin Location", self.location, BEACON_TEST_KEY, "ble_key")
		for switch, user, expected in (
			(1, USER, True),
			(0, USER, False),
			(1, OTHER_USER, False),
			(1, NO_EMPLOYEE_USER, False),
		):
			frappe.set_user("Administrator")
			frappe.db.set_single_value("HR Settings", "ble_checkin_enabled", switch)
			frappe.set_user(user)
			self.assertIs(mobile.get_boot()["features"]["ble_checkin"], expected, (switch, user))

	def test_boot_mobile_checkin_follows_hr_settings_like_pwa(self):
		# PWA 用 Boolean(value)：没保存过（None）也算不允许
		for value, expected in ((1, True), (0, False), (None, False)):
			frappe.set_user("Administrator")
			frappe.db.set_single_value("HR Settings", "allow_employee_checkin_from_mobile_app", value)
			frappe.set_user(USER)
			self.assertEqual(mobile.get_boot()["features"]["mobile_checkin"], expected, value)

	def test_boot_profile_collection_off_when_module_missing(self):
		frappe.set_user(USER)
		real_get_attr = frappe.get_attr

		def get_attr(path, *args, **kwargs):
			if "employee_profile" in path:
				raise ImportError("no module")
			return real_get_attr(path, *args, **kwargs)

		with patch.object(mobile.frappe, "get_attr", side_effect=get_attr):
			self.assertFalse(mobile.get_boot()["features"]["profile_collection"])


SUMMARY_WITH_SHIFT = {
	"employee": None,
	"today_entry": {
		"date": None,
		"start_time": "09:00",
		"end_time": "18:00",
		"scheduled_time": "09:00-18:00",
		"hours": 8.0,
		"wr_shift_slot": "9-18",
		"shift_label": "9-18",
		"is_custom": 0,
		"custom_start_time": None,
		"custom_end_time": None,
	},
	"next_entry": None,
	"today_event": {"title": "大促日", "event_type": "Sale", "color": "#F59E0B", "description": "x"},
	"preference_notices": [],
}


class TestHomeSnapshot(MobileApiTestCase):
	def _snapshot(self, summary=None, **patches):
		summary = summary if summary is not None else SUMMARY_WITH_SHIFT
		if summary.get("today_entry"):
			summary = {**summary, "today_entry": {**summary["today_entry"], "date": frappe.utils.nowdate()}}
		with (
			patch.object(mobile, "_schedule_summary", return_value=summary),
			patch.object(mobile, "_scheduled_days", return_value=21),
		):
			if "calendar" in patches:
				with patch.object(mobile, "get_attendance_calendar_events", patches["calendar"]):
					return mobile.get_home_snapshot()
			return mobile.get_home_snapshot()

	def test_snapshot_shape(self):
		frappe.set_user(USER)
		snap = self._snapshot()
		self.assertEqual(
			set(snap),
			{
				"api_version", "today", "now", "first_name", "work_status", "today_shift", "next_shift", "progress",
				"sale_event", "heatmap", "month", "preference_notices", "weather", "checkin", "reminders",
			},
		)
		self.assertEqual(len(snap["heatmap"]["cells"]), 140)
		self.assertEqual(snap["heatmap"]["weeks"], 20)
		self.assertEqual(snap["today_shift"], {"date": frappe.utils.nowdate(), "start_time": "09:00", "end_time": "18:00", "hours": 8.0, "slot": "9-18"})
		self.assertEqual(snap["sale_event"], {"title": "大促日", "event_type": "Sale", "color": "#F59E0B"})
		self.assertIsNone(snap["weather"])
		self.assertEqual(snap["month"]["scheduled_days"], 21)
		self.assertIsNotNone(snap["progress"])
		self.assertEqual(set(snap["checkin"]) >= {"enabled", "has_passkey", "on_office_network", "location_required", "location"}, True)

	def test_snapshot_without_shift_or_checkin(self):
		frappe.set_user(USER)
		snap = self._snapshot(summary={"today_entry": None, "next_entry": None, "today_event": None, "preference_notices": []})
		self.assertIsNone(snap["progress"])
		self.assertIsNone(snap["today_shift"])
		self.assertIsNone(snap["sale_event"])
		self.assertEqual(snap["work_status"]["status"], "no_checkin_today")

	def test_weather_is_gone(self):
		# App 不再显示天气：快照留着 weather 键（已装的旧版 App 照常解码）但永远为 null；
		# 取天气只剩签到牌在服务器内部用，不再对外开放
		import hrms.api

		frappe.set_user(USER)
		self.assertIsNone(self._snapshot()["weather"])
		self.assertFalse(hasattr(hrms.api, "get_weather_forecast"))
		self.assertNotIn(hrms.api.get_weather_data, frappe.whitelisted)

	def test_snapshot_requires_employee(self):
		frappe.set_user(NO_EMPLOYEE_USER)
		with self.assertRaises(frappe.PermissionError):
			mobile.get_home_snapshot()

	def test_snapshot_uses_own_calendar(self):
		frappe.set_user(USER)
		from unittest.mock import MagicMock

		calendar = MagicMock(return_value={})
		self._snapshot(calendar=calendar)
		args, kwargs = calendar.call_args
		self.assertEqual(len(args) + len(kwargs), 2)
		self.assertNotIn("employee", kwargs)

	def test_snapshot_month_counts_half_days(self):
		frappe.set_user(USER)
		# month_half_days 已经按每个半天 0.5 计（get_employee_dashboard_stats 的 SQL），这里是一个半天
		stats = {"month_hours": 20.0, "month_present": 2.0, "month_half_days": 0.5}
		with patch.object(mobile, "get_employee_dashboard_stats", return_value=stats):
			month = self._snapshot()["month"]
		self.assertEqual((month["hours"], month["present_days"], month["average_hours"]), (20.0, 2.5, 8.0))
