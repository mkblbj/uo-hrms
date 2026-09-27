import json
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import passkey
from hrms.tests.utils import HRMSTestSuite
from hrms.tests.webauthn_soft_authenticator import SoftAuthenticator

RP_ID = "localhost"
ORIGIN = "http://localhost:29830"
API_USER = "passkey-api@example.com"
OTHER_USER = "passkey-api-other@example.com"


class PasskeyApiTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.conf = patch.dict(frappe.local.conf, {"passkey_rp_id": RP_ID, "passkey_origins": [ORIGIN]})
		self.conf.start()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(API_USER, company="_Test Company")
		self.other_employee = make_employee(OTHER_USER, company="_Test Company")
		for user in (API_USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
		frappe.db.delete("Passkey Credential", {"user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("PWA Notification", {"to_user": ("in", [API_USER, OTHER_USER])})
		frappe.db.delete("Employee Checkin", {"employee": ("in", [self.employee, self.other_employee])})

	def tearDown(self):
		frappe.set_user("Administrator")
		self.conf.stop()

	def register_device(self, user=API_USER, authenticator=None):
		authenticator = authenticator or SoftAuthenticator(RP_ID, ORIGIN, user.encode())
		frappe.set_user(user)
		options = passkey.register_options()
		response = authenticator.register(options["challenge"])
		passkey.register_complete(json.dumps(response), device_name="Test Phone")
		frappe.set_user("Administrator")
		return authenticator


class TestPasskeyRegistration(PasskeyApiTestCase):
	def test_register_stores_verified_public_key(self):
		authenticator = self.register_device()
		row = frappe.db.get_value(
			"Passkey Credential",
			{"credential_id": authenticator.credential_id_b64},
			["employee", "credential_public_key", "device_name"],
			as_dict=True,
		)
		self.assertEqual(row.employee, self.employee)
		self.assertTrue(row.credential_public_key)
		self.assertEqual(row.device_name, "Test Phone")

	def test_register_rejects_reused_or_foreign_challenge(self):
		authenticator = SoftAuthenticator(RP_ID, ORIGIN)
		frappe.set_user(OTHER_USER)
		options = passkey.register_options()
		frappe.set_user(API_USER)
		response = authenticator.register(options["challenge"])
		with self.assertRaises(frappe.ValidationError):
			passkey.register_complete(json.dumps(response))

	def test_device_limit_and_new_device_notification(self):
		self.register_device()
		self.assertFalse(frappe.db.exists("PWA Notification", {"to_user": API_USER}))
		self.register_device()
		self.assertTrue(frappe.db.exists("PWA Notification", {"to_user": API_USER}))
		self.register_device()
		frappe.set_user(API_USER)
		with self.assertRaises(frappe.ValidationError):
			passkey.register_options()

	def test_options_exclude_existing_devices(self):
		authenticator = self.register_device()
		frappe.set_user(API_USER)
		options = passkey.register_options()
		self.assertEqual([c["id"] for c in options["excludeCredentials"]], [authenticator.credential_id_b64])

	def test_list_and_delete_only_own_devices(self):
		self.register_device()
		self.register_device(user=OTHER_USER)
		frappe.set_user(API_USER)
		mine = passkey.get_my_passkeys()
		self.assertEqual(len(mine), 1)
		other_name = frappe.db.get_value("Passkey Credential", {"user": OTHER_USER}, "name")
		with self.assertRaises(frappe.ValidationError):
			passkey.delete_passkey(other_name)
		passkey.delete_passkey(mine[0]["name"])
		self.assertEqual(passkey.get_my_passkeys(), [])
