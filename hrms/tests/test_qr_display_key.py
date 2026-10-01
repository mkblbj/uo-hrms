import frappe

from hrms.api.qr_attendance import generate_qr_token
from hrms.hr.doctype.qr_checkin_location.qr_checkin_location import get_display_url, verify_display_key
from hrms.tests.utils import HRMSTestSuite
from hrms.www import qr_display

LOCATION = "display-key-door"


class TestQRDisplayKey(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("QR Checkin Location", LOCATION):
			frappe.get_doc(
				{"doctype": "QR Checkin Location", "location_name": LOCATION, "secret": "s" * 32}
			).insert()
		self._require(0)
		self.key = frappe.get_doc("QR Checkin Location", LOCATION).get_password("display_key")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.form_dict.clear()

	def _require(self, value):
		frappe.db.set_value("QR Checkin Location", LOCATION, "require_display_key", value)

	def test_key_is_generated_and_not_required_by_default(self):
		self.assertTrue(self.key)
		frappe.set_user("Guest")
		self.assertTrue(generate_qr_token(LOCATION)["token"])

	def test_required_key_blocks_guests_without_it(self):
		self._require(1)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			generate_qr_token(LOCATION)
		with self.assertRaises(frappe.PermissionError):
			generate_qr_token(LOCATION, key="wrong")
		self.assertTrue(generate_qr_token(LOCATION, key=self.key)["token"])
		self.assertFalse(verify_display_key(LOCATION, None))

	def test_display_page_checks_key_and_hides_location_list(self):
		self._require(1)
		frappe.set_user("Guest")
		frappe.form_dict.update({"location": LOCATION})
		with self.assertRaises(frappe.PermissionError):
			qr_display.get_context(frappe._dict())
		frappe.form_dict.update({"key": self.key})
		self.assertEqual(qr_display.get_context(frappe._dict()).location_name, LOCATION)
		frappe.form_dict.clear()
		with self.assertRaises(frappe.PermissionError):
			qr_display.get_context(frappe._dict())

	def test_display_url_contains_key_for_hr_only(self):
		url = get_display_url(LOCATION)
		self.assertIn(f"location={LOCATION}", url)
		self.assertIn("key=", url)
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_display_url(LOCATION)
