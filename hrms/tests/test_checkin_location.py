from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.utils import getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import checkin_location, qr_attendance
from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type
from hrms.tests.utils import HRMSTestSuite

USER = "checkin-location@example.com"
OFFICE_IP = "203.0.113.5"
MOBILE_IP = "198.51.100.1"
OFFICE = "Checkin Location Test Office"
LOCATION = "checkin-location-test-door"
# 打卡点在 (35.6812, 139.7671)，半径 200 米
NEAR = (35.6813, 139.7672)  # 约 14 米
FAR = (35.6912, 139.7671)  # 约 1.1 公里


def ensure_geofenced_location():
	if not frappe.db.exists("Shift Location", OFFICE):
		frappe.get_doc(
			{
				"doctype": "Shift Location",
				"location_name": OFFICE,
				"latitude": 35.6812,
				"longitude": 139.7671,
				"checkin_radius": 200,
			}
		).insert()
	if not frappe.db.exists("QR Checkin Location", LOCATION):
		frappe.get_doc(
			{"doctype": "QR Checkin Location", "location_name": LOCATION, "secret": "s" * 32}
		).insert()
	frappe.db.set_value("QR Checkin Location", LOCATION, "shift_location", OFFICE)


class CheckinLocationTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee(USER, company="_Test Company")
		frappe.get_doc("User", USER).add_roles("Employee")
		frappe.db.delete("Employee Checkin", {"employee": self.employee})
		frappe.db.delete("Shift Assignment", {"employee": self.employee})
		frappe.db.delete("Error Log", {"method": ("like", "Checkin Location Failure%")})
		frappe.cache.delete_value(f"hrms:checkin-location-failures:{USER}")
		ensure_geofenced_location()
		settings = frappe.get_doc("HR Settings")
		settings.qr_checkin_allowed_ips = "203.0.113.0/24"
		settings.save()
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)

	def qr(self, ip, coordinates=(None, None)):
		secret = frappe.get_doc("QR Checkin Location", LOCATION).get_password("secret")
		slot = qr_attendance._get_time_slot()
		token = f"{LOCATION}|{slot}|{qr_attendance._sign(LOCATION, slot, secret)}"
		frappe.set_user(USER)
		with (
			patch.object(qr_attendance, "get_client_ip", return_value=ip),
			patch("frappe.publish_realtime"),
		):
			return qr_attendance.qr_checkin(token, "IN", *coordinates)

	def checkin_far_away(self, evidence):
		"""排班带地点的员工，在远处打一条卡（由受信接口按给定证据建记录）。"""
		shift_type = setup_shift_type(shift_type="_Test Checkin Location Shift")
		make_shift_assignment(shift_type.name, self.employee, getdate(), shift_location=OFFICE)
		doc = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"log_type": "IN",
				"time": f"{getdate()} 08:30:00",
				"latitude": FAR[0],
				"longitude": FAR[1],
			}
		)
		doc.flags.trusted_checkin_source = True
		doc.flags.presence_evidence = evidence
		return doc.insert(ignore_permissions=True)

	def checkins(self):
		frappe.set_user("Administrator")
		return frappe.get_all(
			"Employee Checkin",
			filters={"employee": self.employee},
			fields=["latitude", "longitude", "checkin_method"],
		)


class TestLocationRequirement(CheckinLocationTestCase):
	def _requirement(self, ip):
		frappe.set_user(USER)
		with patch.object(checkin_location, "get_client_ip", return_value=ip):
			return checkin_location.get_location_requirement()

	def test_office_network_needs_no_location(self):
		self.assertEqual(
			self._requirement(OFFICE_IP), {"location_required": False, "on_office_network": True}
		)

	def test_mobile_data_needs_location(self):
		self.assertEqual(
			self._requirement(MOBILE_IP), {"location_required": True, "on_office_network": False}
		)

	def test_no_location_needed_when_tracking_is_off(self):
		frappe.db.set_single_value("HR Settings", "allow_geolocation_tracking", 0)
		self.assertEqual(
			self._requirement(MOBILE_IP), {"location_required": False, "on_office_network": False}
		)


class TestQrCheckinPresence(CheckinLocationTestCase):
	_qr = CheckinLocationTestCase.qr

	def test_office_network_checks_in_without_location(self):
		result = self._qr(OFFICE_IP)
		self.assertEqual(result["status"], "ok")
		[row] = self.checkins()
		self.assertEqual(row.checkin_method, "QR")
		self.assertFalse(row.latitude or row.longitude)

	def test_mobile_data_without_location_is_asked_for_it(self):
		self.assertEqual(self._qr(MOBILE_IP), {"status": "need_location"})
		self.assertEqual(self.checkins(), [])

	def test_mobile_data_inside_radius_checks_in(self):
		self.assertEqual(self._qr(MOBILE_IP, NEAR)["status"], "ok")
		[row] = self.checkins()
		self.assertAlmostEqual(row.latitude, NEAR[0], places=4)

	def test_mobile_data_outside_radius_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._qr(MOBILE_IP, FAR)
		self.assertEqual(self.checkins(), [])

	def test_office_network_is_trusted_over_rough_gps(self):
		self.assertEqual(self._qr(OFFICE_IP, FAR)["status"], "ok")
		[row] = self.checkins()
		self.assertAlmostEqual(row.latitude, FAR[0], places=4)


class TestShiftGeofenceWithOfficeNetwork(CheckinLocationTestCase):
	"""排班带地点的员工，Employee Checkin 自己还会按排班地点查一次距离。"""

	def test_office_network_skips_the_shift_distance_check(self):
		self.assertTrue(self.checkin_far_away("office_network").name)

	def test_gps_outside_the_shift_radius_is_still_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self.checkin_far_away("gps")


class TestEditingSavedCheckins(CheckinLocationTestCase):
	"""位置只在打卡那一刻核对；HR 事后在后台改别的字段不该被定位规则拦住。"""

	def test_hr_can_edit_an_office_network_checkin_later(self):
		self.qr(OFFICE_IP)
		frappe.set_user("Administrator")
		name = frappe.db.get_value("Employee Checkin", {"employee": self.employee})
		doc = frappe.get_doc("Employee Checkin", name)
		doc.skip_auto_attendance = 1
		doc.save()
		self.assertEqual(frappe.db.get_value("Employee Checkin", name, "skip_auto_attendance"), 1)

	def test_moving_the_coordinates_later_is_checked_again(self):
		doc = frappe.get_doc("Employee Checkin", self.checkin_far_away("office_network").name)
		doc.latitude = FAR[0] + 0.01
		with self.assertRaises(frappe.ValidationError):
			doc.save()


class TestLocationFailureReport(CheckinLocationTestCase):
	def _report(self, *args):
		frappe.set_user(USER)
		return checkin_location.report_location_failure(*args)

	def _reports(self):
		frappe.set_user("Administrator")
		return frappe.get_all(
			"Error Log",
			filters={"method": ("like", "Checkin Location Failure%"), "owner": USER},
			fields=["method", "error"],
		)

	def test_records_reason_flow_and_wait(self):
		self._report("qr", "denied", 1234)
		[log] = self._reports()
		self.assertEqual(log.method, "Checkin Location Failure - denied")
		self.assertIn("qr", log.error)
		self.assertIn("1234", log.error)

	def test_records_phone_model_and_system_version(self):
		agent = (
			"Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
			"AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
		)
		request = SimpleNamespace(headers={"User-Agent": agent})
		with patch.object(frappe.local, "request", request, create=True):
			self._report("qr", "timeout", 8000)
		[log] = self._reports()
		self.assertIn("iPhone iOS 18.5", log.error)

	def test_rejects_unknown_reason_or_flow(self):
		for args in (("qr", "hacked", 1), ("nfc", "denied", 1)):
			with self.subTest(args=args), self.assertRaises(frappe.ValidationError):
				self._report(*args)
		self.assertEqual(self._reports(), [])

	def test_users_without_an_employee_record_are_not_logged(self):
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Employee", {"user_id": "Administrator"}))
		self.assertEqual(checkin_location.report_location_failure("qr", "denied", 1), {"status": "skipped"})
		self.assertFalse(
			frappe.db.exists(
				"Error Log", {"method": ("like", "Checkin Location Failure%"), "owner": "Administrator"}
			)
		)

	def test_a_counter_left_without_expiry_gets_one(self):
		key = frappe.cache.make_key(f"hrms:checkin-location-failures:{USER}")
		frappe.cache.set(key, 3)  # 上次设过期失败留下的计数
		self._report("qr", "timeout", 1)
		self.assertGreater(frappe.cache.ttl(key), 0)

	def test_caps_reports_at_twenty_per_user_per_hour(self):
		for _ in range(25):
			self._report("passkey", "timeout", 8000)
		self.assertEqual(len(self._reports()), 20)
