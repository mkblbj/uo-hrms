import importlib
import unittest

import frappe


class TestEmployeeProfileCollection(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("profile_collection_test")
		self.previous_users = frappe.conf.get("pwa_profile_collection_users")
		self.previous_enabled = frappe.conf.get("pwa_profile_collection_enabled")
		self.addCleanup(self.cleanup_records)
		self.users = ["profile-collection-pilot@example.com", "profile-collection-other@example.com"]
		self.employees = []
		for index, user in enumerate(self.users):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": f"Profile Test {index}",
					"send_welcome_email": 0,
					"roles": [{"role": "Employee"}],
				}
			).insert()
			doc = frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": f"Profile Test {index}",
					"company": "_Test Company",
					"naming_series": frappe.get_meta("Employee")
					.get_field("naming_series")
					.options.splitlines()[0],
					"gender": "Female",
					"date_of_birth": "1990-01-01",
					"date_of_joining": "2026-01-01",
					"status": "Active",
					"user_id": user,
					"cell_number": "09001234567",
					"current_address": "東京都\n旧住所",
					"person_to_be_contacted": "旧联系人",
					"relation": "父亲",
					"emergency_phone_number": "09011112222",
				}
			).insert(set_name=f"_PROFILE-COLLECTION-TEST-{index}")
			self.employees.append(doc.name)
		frappe.conf.pwa_profile_collection_users = self.users[:1]
		frappe.conf.pwa_profile_collection_enabled = False
		frappe.set_user(self.users[0])

	def cleanup_records(self):
		frappe.set_user("Administrator")
		frappe.conf.pwa_profile_collection_users = self.previous_users
		frappe.conf.pwa_profile_collection_enabled = self.previous_enabled
		frappe.db.rollback(save_point="profile_collection_test")
		frappe.clear_cache()

	def api(self):
		return importlib.import_module("hrms.api.employee_profile")

	def payload(self):
		profile = self.api().get_my_profile()
		return {
			"cell_number": "+81-90-0000-0000",
			"custom_wechat_id": "profile_wechat",
			"current_address": "大阪府大阪市\n新住所 302",
			"contact_email": "contact@example.com",
			"person_to_be_contacted": "紧急联系人测试",
			"relation": "配偶",
			"emergency_phone_number": "+86-13800001111",
			"modified": profile["modified"],
		}

	def test_entry_is_only_enabled_for_the_configured_active_employee(self):
		self.assertEqual(self.api().get_collection_status(), {"enabled": True})
		for user in [self.users[1], "Administrator", "Guest"]:
			frappe.set_user(user)
			self.assertEqual(self.api().get_collection_status(), {"enabled": False})

	def test_all_enabled_active_employees_can_fill_only_their_own_profile(self):
		frappe.conf.pwa_profile_collection_enabled = True
		frappe.conf.pwa_profile_collection_users = []
		for user, employee in zip(self.users, self.employees, strict=True):
			frappe.set_user(user)
			self.assertEqual(self.api().get_collection_status(), {"enabled": True})
			self.assertEqual(self.api().get_my_profile()["employee"], employee)
		self.assertFalse(frappe.has_permission("Employee", "write", self.employees[1]))
		before = frappe.db.get_value(
			"Employee", self.employees[0], ["cell_number", "current_address", "modified"]
		)
		result = self.api().save_my_profile(self.payload())
		self.assertEqual(result["employee"], self.employees[1])
		self.assertEqual(result["cell_number"], "+81-90-0000-0000")
		self.assertEqual(
			frappe.db.get_value(
				"Employee", self.employees[0], ["cell_number", "current_address", "modified"]
			),
			before,
		)

	def test_all_mode_still_rejects_inactive_disabled_unlinked_and_guest_accounts(self):
		frappe.conf.pwa_profile_collection_enabled = True
		frappe.conf.pwa_profile_collection_users = []
		payload = self.payload()
		for status in ["Left", "Inactive", "Suspended"]:
			frappe.db.set_value("Employee", self.employees[0], "status", status)
			self.assertEqual(self.api().get_collection_status(), {"enabled": False})
			with self.assertRaises(frappe.PermissionError):
				self.api().get_my_profile()
			with self.assertRaises(frappe.PermissionError):
				self.api().save_my_profile(payload)
		frappe.db.set_value("Employee", self.employees[0], "status", "Active")
		frappe.db.set_value("User", self.users[0], "enabled", 0)
		self.assertEqual(self.api().get_collection_status(), {"enabled": False})
		with self.assertRaises(frappe.PermissionError):
			self.api().save_my_profile(payload)
		frappe.db.set_value("User", self.users[0], "enabled", 1)
		frappe.db.set_value("Employee", self.employees[0], "user_id", "")
		self.assertEqual(self.api().get_collection_status(), {"enabled": False})
		with self.assertRaises(frappe.PermissionError):
			self.api().get_my_profile()
		frappe.set_user("Guest")
		self.assertEqual(self.api().get_collection_status(), {"enabled": False})
		with self.assertRaises(frappe.PermissionError):
			self.api().save_my_profile(payload)

	def test_turning_off_all_mode_returns_to_explicit_pilot_access(self):
		frappe.conf.pwa_profile_collection_enabled = True
		frappe.set_user(self.users[1])
		self.assertEqual(self.api().get_collection_status(), {"enabled": True})
		frappe.conf.pwa_profile_collection_enabled = False
		self.assertEqual(self.api().get_collection_status(), {"enabled": False})
		frappe.set_user(self.users[0])
		self.assertEqual(self.api().get_collection_status(), {"enabled": True})

	def test_empty_or_malformed_pilot_configuration_does_not_enable_anyone(self):
		for value in [None, [], self.users[0], True, {self.users[0]: True}]:
			frappe.conf.pwa_profile_collection_users = value
			self.assertEqual(self.api().get_collection_status(), {"enabled": False})

	def test_non_pilot_cannot_read_or_save_even_by_calling_the_api(self):
		payload = self.payload()
		for user in [self.users[1], "Guest"]:
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				self.api().get_my_profile()
			with self.assertRaises(frappe.PermissionError):
				self.api().save_my_profile(payload)

	def test_get_returns_only_own_profile_and_prefills_account_email(self):
		profile = self.api().get_my_profile()
		self.assertEqual(profile["employee"], self.employees[0])
		self.assertEqual(profile["contact_email"], self.users[0])
		self.assertEqual(profile["person_to_be_contacted"], "旧联系人")
		self.assertEqual(profile["relation"], "父亲")
		self.assertEqual(profile["emergency_phone_number"], "09011112222")
		self.assertEqual(
			set(profile),
			{
				"employee",
				"employee_name",
				"employee_number",
				"cell_number",
				"custom_wechat_id",
				"current_address",
				"contact_email",
				"person_to_be_contacted",
				"relation",
				"emergency_phone_number",
				"modified",
			},
		)

	def test_employee_can_save_own_contacts_and_hr_overview_reads_the_same_record(self):
		from hrms.hr.report.employee_information_overview.employee_information_overview import execute

		self.assertFalse(frappe.has_permission("Employee", "write", self.employees[0]))
		other_before = frappe.db.get_value(
			"Employee", self.employees[1], ["cell_number", "current_address", "personal_email"]
		)
		payload = self.payload()
		profile = self.api().save_my_profile(payload)
		for field in [
			"cell_number",
			"custom_wechat_id",
			"current_address",
			"contact_email",
			"person_to_be_contacted",
			"relation",
			"emergency_phone_number",
		]:
			self.assertEqual(profile[field], payload[field])
		frappe.set_user("Administrator")
		row = execute({"search": self.employees[0]})[1][0]
		self.assertEqual(row["contact_email"], payload["contact_email"])
		self.assertEqual(row["cell_number"], payload["cell_number"])
		self.assertEqual(row["current_address"], payload["current_address"])
		self.assertEqual(row["custom_wechat_id"], payload["custom_wechat_id"])
		for field in ["person_to_be_contacted", "relation", "emergency_phone_number"]:
			self.assertEqual(row[field], payload[field])
		self.assertEqual(frappe.db.get_value("Employee", self.employees[0], "user_id"), self.users[0])
		self.assertEqual(frappe.db.get_value("User", self.users[0], "email"), self.users[0])
		self.assertEqual(
			frappe.db.get_value(
				"Employee", self.employees[1], ["cell_number", "current_address", "personal_email"]
			),
			other_before,
		)

	def test_extra_fields_cannot_target_another_employee_or_modify_protected_fields(self):
		payload = self.payload()
		for field in ["employee", "name", "user_id", "status", "company_email", "bank_ac_no"]:
			with self.subTest(field=field):
				with self.assertRaises(frappe.ValidationError):
					self.api().save_my_profile({**payload, field: self.employees[1]})
		self.assertEqual(frappe.db.get_value("Employee", self.employees[0], "status"), "Active")

	def test_required_fields_invalid_email_and_non_text_values_are_rejected(self):
		payload = self.payload()
		for field, value in [
			("cell_number", " \t "),
			("current_address", "\n "),
			("contact_email", ""),
			("contact_email", "invalid-address"),
			("custom_wechat_id", {"unsafe": True}),
			("person_to_be_contacted", " \t "),
			("relation", ""),
			("emergency_phone_number", "\n "),
			("emergency_phone_number", {"unsafe": True}),
		]:
			with self.subTest(field=field, value=value):
				with self.assertRaises(frappe.ValidationError):
					self.api().save_my_profile({**payload, field: value})

	def test_wechat_is_optional_and_phone_leading_zero_is_preserved(self):
		payload = self.payload()
		profile = self.api().save_my_profile(
			{**payload, "cell_number": "09001234567", "custom_wechat_id": ""}
		)
		self.assertEqual(profile["cell_number"], "09001234567")
		self.assertEqual(profile["custom_wechat_id"], "")

	def test_existing_company_contact_email_is_updated_without_renaming_the_account(self):
		frappe.db.set_value(
			"Employee",
			self.employees[0],
			{"company_email": "old-work@example.com", "personal_email": "private@example.com"},
		)
		payload = self.payload()
		self.api().save_my_profile(payload)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employees[0], "company_email"), payload["contact_email"]
		)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employees[0], "personal_email"), "private@example.com"
		)
		self.assertEqual(frappe.db.get_value("User", self.users[0], "email"), self.users[0])

	def test_pilot_removal_between_loading_and_saving_revokes_access(self):
		payload = self.payload()
		frappe.conf.pwa_profile_collection_users = []
		with self.assertRaises(frappe.PermissionError):
			self.api().save_my_profile(payload)

	def test_inactive_employee_and_disabled_account_cannot_read_or_save(self):
		payload = self.payload()
		for status in ["Left", "Inactive", "Suspended"]:
			frappe.db.set_value("Employee", self.employees[0], "status", status)
			self.assertEqual(self.api().get_collection_status(), {"enabled": False})
			with self.assertRaises(frappe.PermissionError):
				self.api().save_my_profile(payload)
		frappe.db.set_value("Employee", self.employees[0], "status", "Active")
		frappe.db.set_value("User", self.users[0], "enabled", 0)
		self.assertEqual(self.api().get_collection_status(), {"enabled": False})
		with self.assertRaises(frappe.PermissionError):
			self.api().get_my_profile()

	def test_hr_changes_are_not_overwritten_by_an_older_form(self):
		payload = self.payload()
		frappe.db.set_value("Employee", self.employees[0], "current_address", "HR 更新后的地址")
		with self.assertRaises(frappe.TimestampMismatchError):
			self.api().save_my_profile(payload)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employees[0], "current_address"), "HR 更新后的地址"
		)
