import frappe
from frappe.utils import now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.tests.utils import HRMSTestSuite

GUARD_USER = "checkin-guard@example.com"


def _checkin_doc(employee, **overrides):
	data = {"doctype": "Employee Checkin", "employee": employee, "log_type": "IN", "time": now_datetime()}
	data.update(overrides)
	return frappe.get_doc(data)


class TestEmployeeCheckinGuard(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.employee = make_employee(GUARD_USER, company="_Test Company")
		frappe.get_doc("User", GUARD_USER).add_roles("Employee")
		frappe.db.delete("Employee Checkin", {"employee": self.employee})

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_employee_cannot_insert_checkin_directly(self):
		frappe.set_user(GUARD_USER)
		with self.assertRaises(frappe.PermissionError):
			_checkin_doc(self.employee).insert(ignore_permissions=True)

	def test_trusted_source_can_insert_for_employee_session(self):
		frappe.set_user(GUARD_USER)
		doc = _checkin_doc(self.employee)
		doc.flags.trusted_checkin_source = True
		doc.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Employee Checkin", doc.name))

	def test_employee_cannot_change_time_or_delete(self):
		doc = _checkin_doc(self.employee)
		doc.insert()
		frappe.set_user(GUARD_USER)
		doc.reload()
		doc.time = "2026-01-01 09:00:00"
		with self.assertRaises(frappe.PermissionError):
			doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.delete_doc("Employee Checkin", doc.name, ignore_permissions=True)

	def test_hr_user_is_not_blocked(self):
		frappe.set_user("Administrator")
		doc = _checkin_doc(self.employee, checkin_method="QR")
		doc.insert()
		doc.time = "2026-01-01 09:00:00"
		doc.save()
		self.assertEqual(frappe.db.get_value("Employee Checkin", doc.name, "checkin_method"), "QR")

	def test_permission_patch_removes_self_service_writes(self):
		from hrms.patches.v16_0.restrict_employee_checkin_self_service_permissions import execute

		execute()
		for ptype in ("create", "write", "delete"):
			self.assertFalse(frappe.has_permission("Employee Checkin", ptype, user=GUARD_USER), msg=ptype)
		self.assertTrue(frappe.has_permission("Employee Checkin", "read", user=GUARD_USER))

	def test_backfill_patch_sets_methods(self):
		from hrms.patches.v16_0.backfill_employee_checkin_method import execute

		location = "guard-test-door"
		if not frappe.db.exists("QR Checkin Location", location):
			frappe.get_doc(
				{"doctype": "QR Checkin Location", "location_name": location, "secret": "s" * 32}
			).insert()
		rows = {
			"nfc": _checkin_doc(
				self.employee, device_id=f"NFC-Passkey:{location}", time="2026-01-01 09:00:00"
			),
			"qr": _checkin_doc(self.employee, device_id=location, time="2026-01-01 18:00:00", log_type="OUT"),
			"fix": _checkin_doc(self.employee, device_id="Attendance Correction", time="2026-01-02 09:00:00"),
		}
		for doc in rows.values():
			doc.insert()
		execute()

		def method_of(key):
			return frappe.db.get_value("Employee Checkin", rows[key].name, "checkin_method")

		self.assertEqual(
			(method_of("nfc"), method_of("qr"), method_of("fix")),
			("NFC Passkey", "QR", "Attendance Correction"),
		)
