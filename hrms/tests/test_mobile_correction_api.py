"""补卡接口给原生 App 的补充：审批人、班次、我处理过的申请、写接口只收 POST。"""

from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import attendance_correction as api
from hrms.api import mobile
from hrms.tests.test_mobile_api import ensure_user
from hrms.tests.utils import HRMSTestSuite

USER = "mobile-correction@example.com"
APPROVER = "mobile-correction-approver@example.com"
OTHER_APPROVER = "mobile-correction-other-approver@example.com"
DAY = "2026-05-20"


def make_request(employee, day, log_type="IN"):
	return frappe.get_doc(
		{
			"doctype": "Attendance Correction Request",
			"employee": employee,
			"attendance_date": day,
			"request_type": "Forgot Check-in" if log_type == "IN" else "Forgot Check-out",
			"requested_log_type": log_type,
			"requested_time": f"{day} {'09:00:00' if log_type == 'IN' else '18:00:00'}",
			"reason": "forgot",
			"status": "Pending",
		}
	).insert(ignore_permissions=True)


def mark_processed(request, status, user, approved_on, rejection_reason=None):
	frappe.db.set_value(
		"Attendance Correction Request",
		request.name,
		{"status": status, "approved_by": user, "approved_on": approved_on, "rejection_reason": rejection_reason},
	)


class TestMobileCorrectionApi(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		for user in (APPROVER, OTHER_APPROVER):
			ensure_user(user)
		self.employee = make_employee(USER, company="_Test Company")
		frappe.get_doc("User", USER).add_roles("Employee")
		frappe.db.set_value("Employee", self.employee, {"attendance_correction_approver": APPROVER, "department": None})

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_context_has_approver_and_scheduled_shift(self):
		entry = {"date": DAY, "start_time": "09:00", "end_time": "18:00", "hours": 8.0, "shift_label": "9-18"}
		frappe.set_user(USER)
		with patch.object(mobile, "_roster_entry", return_value=entry) as roster_entry:
			context = api.get_attendance_correction_context(DAY)
		# 取的是申请人本人的排班（审批人看别人的申请时也一样）
		self.assertEqual(roster_entry.call_args.args[0], self.employee)
		self.assertEqual(context["approver"], {"user": APPROVER, "full_name": frappe.db.get_value("User", APPROVER, "full_name")})
		self.assertEqual(
			context["scheduled_shift"],
			{"start": "2026-05-20 09:00:00", "end": "2026-05-20 18:00:00", "slot": "9-18", "hours": 8.0},
		)
		# 原有的 shift 是 Shift Type 名字（PWA 在用），保持原样
		self.assertIn("shift", context)
		self.assertNotIsInstance(context["shift"], dict)

	def test_context_without_approver(self):
		frappe.db.set_value("Employee", self.employee, "attendance_correction_approver", None)
		frappe.set_user(USER)
		with patch.object(mobile, "_roster_entry", return_value=None):
			context = api.get_attendance_correction_context(DAY)
		self.assertIsNone(context["approver"])
		self.assertIsNone(context["scheduled_shift"])

	def test_context_survives_roster_errors(self):
		# 新字段出错不能拖垮 PWA 在用的上下文接口：只让 scheduled_shift 为 null
		frappe.set_user(USER)
		with patch.object(mobile, "_roster_entry", side_effect=RuntimeError("roster down")), patch.object(frappe, "log_error"):
			context = api.get_attendance_correction_context(DAY)
		self.assertIsNone(context["scheduled_shift"])
		self.assertEqual(context["approver"]["user"], APPROVER)
		self.assertEqual(context["attendance_date"], DAY)

	def test_processed_lists_only_mine(self):
		approved = make_request(self.employee, "2026-05-18")
		rejected = make_request(self.employee, "2026-05-19")
		by_other = make_request(self.employee, "2026-05-20")
		pending = make_request(self.employee, "2026-05-21")
		mark_processed(approved, "Applied", APPROVER, "2026-05-22 10:00:00")
		mark_processed(rejected, "Rejected", APPROVER, "2026-05-22 11:00:00", "打刻あり")
		mark_processed(by_other, "Applied", OTHER_APPROVER, "2026-05-22 12:00:00")

		frappe.set_user(APPROVER)
		rows = api.get_processed_attendance_correction_approvals()
		self.assertEqual([row["name"] for row in rows], [rejected.name, approved.name])
		self.assertNotIn(pending.name, [row["name"] for row in rows])
		self.assertEqual(rows[0]["status"], "Rejected")
		self.assertEqual(rows[0]["rejection_reason"], "打刻あり")
		self.assertEqual(str(rows[0]["approved_on"]), "2026-05-22 11:00:00")
		self.assertEqual(
			set(rows[0]),
			{
				"name", "employee", "employee_name", "attendance_date", "request_type", "requested_log_type",
				"requested_time", "status", "creation", "reason", "approved_on", "rejection_reason",
			},
		)
		self.assertEqual(len(api.get_processed_attendance_correction_approvals(limit=1)), 1)

	def test_writes_are_post_only(self):
		for fn in (
			api.submit_attendance_correction_request,
			api.approve_attendance_correction_request,
			api.reject_attendance_correction_request,
		):
			self.assertEqual(tuple(frappe.allowed_http_methods_for_whitelisted_func[fn]), ("POST",), fn.__name__)
		# Frappe 会给只读接口自动加上 QUERY
		methods = frappe.allowed_http_methods_for_whitelisted_func[api.get_processed_attendance_correction_approvals]
		self.assertIn("GET", methods)
		self.assertNotIn("POST", methods)
