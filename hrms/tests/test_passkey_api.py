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
	rp_id = RP_ID
	origin = ORIGIN

	def setUp(self):
		frappe.set_user("Administrator")
		self.conf = patch.dict(
			frappe.local.conf, {"passkey_rp_id": self.rp_id, "passkey_origins": [self.origin]}
		)
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
		authenticator = authenticator or SoftAuthenticator(self.rp_id, self.origin, user.encode())
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


NFC_LOCATION = "passkey-test-door"


def ensure_location(with_geofence=True):
	if not frappe.db.exists("Shift Location", "Passkey Test Office"):
		frappe.get_doc(
			{
				"doctype": "Shift Location",
				"location_name": "Passkey Test Office",
				"latitude": 35.6812,
				"longitude": 139.7671,
				"checkin_radius": 200,
			}
		).insert()
	if not frappe.db.exists("QR Checkin Location", NFC_LOCATION):
		frappe.get_doc(
			{"doctype": "QR Checkin Location", "location_name": NFC_LOCATION, "secret": "s" * 32}
		).insert()
	frappe.db.set_value(
		"QR Checkin Location",
		NFC_LOCATION,
		"shift_location",
		"Passkey Test Office" if with_geofence else None,
	)
	return NFC_LOCATION


class TestNfcPasskeyCheckin(PasskeyApiTestCase):
	rp_id = "erphr.toiroworld.com"
	origin = "https://erphr.toiroworld.com"

	def _nfc(self, authenticator, *, latitude=35.6813, longitude=139.7672, location=None, **kwargs):
		location = location or ensure_location()
		frappe.set_user("Guest")
		options = passkey.auth_options(location)
		assertion = authenticator.authenticate(options["challenge"], **kwargs)
		with patch("frappe.publish_realtime"):
			return passkey.passkey_checkin(json.dumps(assertion), location, latitude, longitude)

	def test_guest_nfc_checkin_with_valid_passkey_and_location(self):
		authenticator = self.register_device()
		result = self._nfc(authenticator)
		frappe.set_user("Administrator")
		self.assertEqual(result["status"], "ok")
		self.assertEqual(result["log_type"], "IN")
		row = frappe.db.get_value(
			"Employee Checkin", {"employee": self.employee}, ["device_id", "checkin_method"], as_dict=True
		)
		self.assertEqual((row.device_id, row.checkin_method), (NFC_LOCATION, "NFC Passkey"))

	def test_forged_signature_is_rejected(self):
		authenticator = self.register_device()
		with self.assertRaisesRegex(frappe.ValidationError, "could not be verified"):
			self._nfc(authenticator, tamper_signature=True)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Employee Checkin", {"employee": self.employee}))

	def test_unknown_location_is_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			passkey.auth_options("no-such-door")

	def test_far_away_nfc_checkin_is_rejected(self):
		authenticator = self.register_device()
		with self.assertRaisesRegex(frappe.ValidationError, "confirm you are at the office"):
			self._nfc(authenticator, latitude=35.75, longitude=139.9)

	def test_unregistered_credential_keeps_old_message(self):
		stranger = SoftAuthenticator(self.rp_id, self.origin)
		with self.assertRaisesRegex(frappe.ValidationError, "Passkey not found"):
			self._nfc(stranger)
