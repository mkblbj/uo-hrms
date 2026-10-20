"""マイページ汇总（S7）和 App 里改密码（S9）。"""

from unittest.mock import patch

import frappe
from frappe.utils.password import check_password, update_password

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import device_key, mobile
from hrms.tests.test_mobile_api import NO_EMPLOYEE_USER, ensure_user
from hrms.tests.test_mobile_roster_api import ensure_department
from hrms.tests.utils import HRMSTestSuite

USER = "mobile-account@example.com"
BOSS = "mobile-account-boss@example.com"
PASSWORD = "Mobile-Account-Pass-1"
NEW_PASSWORD = "Fresh-Quiet-Harbor-27"
COMPLETE_PROFILE = {
	"cell_number": "090-1234-5678",
	"custom_wechat_id": "",
	"current_address": "東京都千代田区1-1",
	"contact_email": "taro@example.com",
	"person_to_be_contacted": "山田 花子",
	"relation": "母",
	"emergency_phone_number": "03-1234-5678",
}


def ensure_link(doctype, name, **values):
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert(ignore_permissions=True)
	return name


class TestMyPage(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_user(NO_EMPLOYEE_USER)
		self.department = ensure_department("Mobile Account Office", "Office")
		self.boss = make_employee(BOSS, company="_Test Company")
		self.employee = make_employee(USER, company="_Test Company")
		frappe.get_doc("User", USER).add_roles("Employee")
		frappe.db.set_value("Employee", self.boss, "employee_name", "上司 太郎")
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"employee_name": "テスト 太郎",
				"employee_number": "UO-0001",
				"department": self.department,
				"designation": ensure_link("Designation", "Engineer", designation_name="Engineer"),
				"reports_to": self.boss,
				"date_of_joining": "2024-04-01",
				"employment_type": ensure_link("Employment Type", "Full-time", employee_type_name="Full-time"),
				"branch": ensure_link("Branch", "本社", branch="本社"),
				"cell_number": "090-1234-5678",
				"company_email": "",
				"personal_email": "taro@example.com",
				"date_of_birth": "1990-04-01",
				"gender": "Male",
				"status": "Active",
			},
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def my_page(self, state=None):
		frappe.set_user(USER)
		with patch.object(mobile, "_profile_collection_state", return_value=state or {"enabled": False, "incomplete": False}):
			return mobile.get_my_page()

	def test_employee_fields(self):
		page = self.my_page()
		self.assertEqual(page["api_version"], 1)
		self.assertRegex(page["today"], r"^\d{4}-\d{2}-\d{2}$")
		self.assertEqual(
			page["employee"],
			{
				"name": self.employee,
				"employee_number": "UO-0001",
				"employee_name": "テスト 太郎",
				"department": "Mobile Account Office",
				"designation": "Engineer",
				"reports_to_name": "上司 太郎",
				"date_of_joining": "2024-04-01",
				"employment_type": "Full-time",
				"company": "_Test Company",
				"branch": "本社",
				"cell_number": "090-1234-5678",
				"company_email": None,
				"personal_email": "taro@example.com",
				"date_of_birth": "1990-04-01",
				"gender": "Male",
			},
		)
		self.assertEqual(set(page["photo"]), {"photo", "has_photo", "temporary", "required", "deadline", "overdue"})
		self.assertEqual(page["profile_collection"], {"enabled": False, "incomplete": False})

	def test_blank_values_are_null_and_number_falls_back(self):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"employee_number": "", "department": None, "reports_to": None, "designation": None, "cell_number": " "},
		)
		employee = self.my_page()["employee"]
		self.assertEqual(employee["employee_number"], self.employee)
		self.assertIsNone(employee["department"])
		self.assertIsNone(employee["reports_to_name"])
		self.assertIsNone(employee["designation"])
		self.assertIsNone(employee["cell_number"])

	def test_without_employee_is_not_403(self):
		frappe.set_user(NO_EMPLOYEE_USER)
		page = mobile.get_my_page()
		self.assertEqual(
			{key: page[key] for key in ("employee", "photo", "profile_collection")},
			{"employee": None, "photo": None, "profile_collection": {"enabled": False, "incomplete": False}},
		)

	def test_profile_collection_state(self):
		frappe.set_user(USER)

		def state(enabled, profile=None, error=None):
			def fake_get_attr(path):
				self.assertEqual(path, "hrms.api.employee_profile.get_my_profile")
				if error:
					raise error
				return lambda: profile

			with (
				patch.object(mobile, "_profile_collection_enabled", return_value=enabled),
				patch.object(frappe, "get_attr", side_effect=fake_get_attr),
			):
				return mobile._profile_collection_state()

		self.assertEqual(state(False), {"enabled": False, "incomplete": False})
		self.assertEqual(state(True, COMPLETE_PROFILE), {"enabled": True, "incomplete": False})
		for field in mobile.PROFILE_REQUIRED_FIELDS:
			with self.subTest(field):
				self.assertEqual(state(True, {**COMPLETE_PROFILE, field: " "}), {"enabled": True, "incomplete": True})
		# 微信号不是必填
		self.assertEqual(state(True, {**COMPLETE_PROFILE, "custom_wechat_id": ""})["incomplete"], False)
		self.assertEqual(state(True, error=frappe.PermissionError()), {"enabled": False, "incomplete": False})
		self.assertEqual(state(True, error=ImportError()), {"enabled": False, "incomplete": False})

	def test_profile_collection_off_never_calls_profile_api(self):
		frappe.set_user(USER)
		with (
			patch.object(mobile, "_profile_collection_enabled", return_value=False),
			patch.object(frappe, "get_attr") as get_attr,
		):
			self.assertEqual(mobile._profile_collection_state(), {"enabled": False, "incomplete": False})
		get_attr.assert_not_called()

	def test_home_snapshot_reminder_follows_incomplete(self):
		from hrms.tests.test_mobile_api import TestHomeSnapshot

		frappe.set_user(USER)
		for incomplete in (True, False):
			with self.subTest(incomplete), patch.object(
				mobile, "_profile_collection_state", return_value={"enabled": True, "incomplete": incomplete}
			):
				snapshot = TestHomeSnapshot._snapshot(self)
			self.assertIs(snapshot["reminders"]["profile_collection"], incomplete)


class TestChangePassword(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_user(USER)
		update_password(USER, PASSWORD)
		scope = mobile.CHANGE_PASSWORD_SCOPE
		frappe.cache.delete_value(
			[device_key._failure_key(USER, scope), device_key._lock_key(USER, scope), device_key._failure_key(USER)]
		)
		self.settings = {"enable_password_policy": 1, "minimum_password_score": 2, "logout_on_password_reset": 1}
		settings = patch.object(frappe, "get_system_settings", side_effect=lambda key: self.settings.get(key))
		settings.start()
		self.addCleanup(settings.stop)
		frappe.set_user(USER)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def change(self, old=PASSWORD, new=NEW_PASSWORD):
		return mobile.change_password(old_password=old, new_password=new)

	def test_ok_changes_password_and_keeps_this_session(self):
		with patch("frappe.sessions.clear_sessions") as clear_sessions:
			self.assertEqual(self.change(), {"status": "ok"})
		check_password(USER, NEW_PASSWORD, delete_tracker_cache=False)
		with self.assertRaises(frappe.AuthenticationError):
			check_password(USER, PASSWORD, delete_tracker_cache=False)
		clear_sessions.assert_called_once_with(user=USER, keep_current=True, force=True)
		self.assertEqual(frappe.session.user, USER)
		self.assertEqual(str(frappe.db.get_value("User", USER, "last_password_reset_date")), frappe.utils.today())

	def test_other_sessions_kept_when_site_does_not_log_out(self):
		self.settings["logout_on_password_reset"] = 0
		with patch("frappe.sessions.clear_sessions") as clear_sessions:
			self.assertEqual(self.change(), {"status": "ok"})
		clear_sessions.assert_not_called()

	def test_wrong_password_and_lockout(self):
		for _ in range(4):
			self.assertEqual(self.change(old="nope"), {"status": "wrong_password"})
		self.assertEqual(self.change(old="nope"), {"status": "too_many_attempts"})
		# 锁住以后输对也不行
		self.assertEqual(self.change(), {"status": "too_many_attempts"})
		check_password(USER, PASSWORD, delete_tracker_cache=False)
		# 和手机钥匙登记分开计数
		self.assertFalse(frappe.cache.exists(device_key._lock_key(USER)))

	def test_correct_password_resets_the_count(self):
		for _ in range(4):
			self.change(old="nope")
		self.assertEqual(self.change(new=PASSWORD), {"status": "same_password"})
		self.assertEqual(self.change(old="nope"), {"status": "wrong_password"})

	def test_same_password(self):
		self.assertEqual(self.change(new=PASSWORD), {"status": "same_password"})

	def test_weak_password_returns_frappe_message(self):
		result = self.change(new="abc")
		self.assertEqual(result["status"], "weak_password")
		self.assertTrue(result["message"])
		self.assertNotIn("<", result["message"])
		check_password(USER, PASSWORD, delete_tracker_cache=False)

	def test_weak_rule_follows_site_policy(self):
		self.settings["enable_password_policy"] = 0
		self.assertEqual(self.change(new="abc12"), {"status": "ok"})

	def test_missing_values_are_417(self):
		for old, new in (("", NEW_PASSWORD), (PASSWORD, ""), (None, NEW_PASSWORD)):
			with self.subTest(old=old, new=new), self.assertRaises(frappe.ValidationError):
				self.change(old=old, new=new)

	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			self.change()
