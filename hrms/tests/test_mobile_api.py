from unittest.mock import patch

import frappe
from frappe.utils import get_system_timezone

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import mobile
from hrms.tests.test_passkey_api import ensure_location
from hrms.tests.utils import HRMSTestSuite

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
			set(boot["features"]), {"mobile_checkin", "passkey_checkin", "geolocation_required", "profile_collection"}
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
