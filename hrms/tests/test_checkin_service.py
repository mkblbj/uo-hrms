from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import checkin_service
from hrms.api.checkin_service import (
	CHECKIN_METHOD_PASSKEY,
	create_checkin,
	resolve_auto_log_type,
	validate_checkin_timing,
)
from hrms.tests.utils import HRMSTestSuite

SERVICE_USER = "checkin-service@example.com"


class TestCheckinService(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(SERVICE_USER, company="_Test Company")
		frappe.db.delete("Employee Checkin", {"employee": self.employee})

	def tearDown(self):
		frappe.set_user("Administrator")

	def _log(self, log_type, minutes_ago):
		doc = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"log_type": log_type,
				"time": now_datetime() - timedelta(minutes=minutes_ago),
			}
		)
		doc.insert()
		return doc

	def test_checkout_within_15_minutes_of_checkin_is_rejected(self):
		self._log("IN", 10)
		with self.assertRaises(frappe.ValidationError):
			validate_checkin_timing(self.employee, "OUT")

	def test_checkin_within_5_minutes_of_checkout_is_rejected(self):
		self._log("OUT", 3)
		with self.assertRaises(frappe.ValidationError):
			validate_checkin_timing(self.employee, "IN")

	def test_same_type_within_5_minutes_is_rejected(self):
		self._log("IN", 2)
		with self.assertRaises(frappe.ValidationError):
			validate_checkin_timing(self.employee, "IN")

	def test_exempt_employee_skips_rules(self):
		self._log("IN", 1)
		with patch.object(checkin_service, "is_checkin_cooldown_exempt", return_value=True):
			validate_checkin_timing(self.employee, "OUT")

	def test_auto_log_type(self):
		self.assertEqual(resolve_auto_log_type(self.employee), "IN")
		self._log("IN", 30)
		self.assertEqual(resolve_auto_log_type(self.employee), "OUT")

	def test_create_checkin_sets_fields_audits_and_notifies(self):
		with (
			patch.object(checkin_service.frappe, "publish_realtime") as publish,
			patch.object(checkin_service.frappe, "log_error") as audit,
		):
			checkin = create_checkin(
				employee=self.employee,
				log_type="IN",
				location="door-a",
				method=CHECKIN_METHOD_PASSKEY,
				latitude=35.1,
				longitude=139.2,
				evidence="gps",
				client_ip="198.51.100.1",
			)
		saved = frappe.db.get_value(
			"Employee Checkin", checkin.name, ["device_id", "checkin_method", "log_type"], as_dict=True
		)
		self.assertEqual((saved.device_id, saved.checkin_method, saved.log_type), ("door-a", "Passkey", "IN"))
		notifications = [
			call for call in publish.call_args_list if call.kwargs.get("event") == "qr_checkin_notification"
		]
		self.assertEqual(len(notifications), 1)
		self.assertEqual(notifications[0].kwargs["room"], "qr_location_door-a")
		self.assertIn("IP: 198.51.100.1", audit.call_args.kwargs["message"])
		self.assertEqual(audit.call_args.kwargs["title"], "Passkey Checkin Audit - IN")

	def test_create_checkin_works_for_employee_session(self):
		frappe.get_doc("User", SERVICE_USER).add_roles("Employee")
		frappe.set_user(SERVICE_USER)
		with patch.object(checkin_service.frappe, "publish_realtime"):
			checkin = create_checkin(employee=self.employee, log_type="IN", location="door-a", method="QR")
		frappe.set_user("Administrator")
		self.assertTrue(frappe.db.exists("Employee Checkin", checkin.name))
