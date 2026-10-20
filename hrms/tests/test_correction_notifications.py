"""补卡申请的通知：提交 → 审批人，批准 / 驳回 → 申请人。"""

from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import attendance_correction as api
from hrms.hr.doctype.attendance_correction_request.attendance_correction_request import (
	AttendanceCorrectionRequest,
)
from hrms.hr.doctype.pwa_notification.pwa_notification import PWANotification
from hrms.tests.test_mobile_api import ensure_user
from hrms.tests.utils import HRMSTestSuite

USER = "correction-notice@example.com"
APPROVER = "correction-notice-approver@example.com"
DAY = "2026-05-20"


def notifications(user):
	return frappe.get_all(
		"PWA Notification",
		filters={"to_user": user, "reference_document_type": "Attendance Correction Request"},
		fields=["*"],
		order_by="creation desc, name desc",
	)


@patch.object(PWANotification, "send_push_notification")
class TestCorrectionNotifications(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		ensure_user(APPROVER)
		self.employee = make_employee(USER, company="_Test Company")
		frappe.get_doc("User", USER).add_roles("Employee")
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"attendance_correction_approver": APPROVER, "department": None, "employee_name": "佐藤 花子"},
		)
		frappe.db.delete("PWA Notification", {"to_user": ["in", [USER, APPROVER]]})

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback()
		super().tearDown()

	def submit(self, log_type="OUT", time="18:05:00"):
		frappe.set_user(USER)
		result = api.submit_attendance_correction_request(
			{
				"attendance_date": DAY,
				"request_type": "Forgot Check-out" if log_type == "OUT" else "Forgot Check-in",
				"requested_log_type": log_type,
				"requested_time": f"{DAY} {time}",
				"reason": "病院に寄ったため",
			}
		)
		frappe.set_user("Administrator")
		return result["name"]

	def test_submit_notifies_approver_after_commit(self, push):
		name = self.submit()
		[row] = notifications(APPROVER)
		self.assertEqual(row.notification_title, "修正申請が届きました")
		self.assertEqual(row.message, "佐藤 花子さん · 5月20日の退勤")
		self.assertEqual(row.notification_type, "Approval")
		self.assertEqual(row.reference_document_name, name)
		self.assertEqual(str(row.reference_date), DAY)
		self.assertEqual(row.from_user, USER)
		self.assertEqual(row.target_route, f"/attendance-corrections/{name}")
		self.assertNotIn("病院", row.message)
		# 插入时不推，提交后才推
		push.assert_not_called()
		self.assertIn(push, frappe.db.after_commit._functions)
		self.assertEqual(notifications(USER), [])

	def test_rollback_drops_the_push(self, push):
		self.submit()
		frappe.db.rollback()
		self.assertNotIn(push, frappe.db.after_commit._functions)
		push.assert_not_called()

	def test_approve_notifies_applicant(self, push):
		name = self.submit()
		frappe.set_user(APPROVER)
		with patch.object(AttendanceCorrectionRequest, "apply_correction"):
			api.approve_attendance_correction_request(name)
		frappe.set_user("Administrator")
		[row] = notifications(USER)
		self.assertEqual(row.notification_title, "修正申請が承認されました")
		self.assertEqual(row.message, "5月20日の退勤 18:05")
		self.assertEqual(row.from_user, APPROVER)
		self.assertEqual(row.notification_type, "Approval")
		self.assertEqual(str(row.reference_date), DAY)

	def test_reject_notifies_applicant_without_reason(self, push):
		name = self.submit(log_type="IN", time="09:03:00")
		frappe.set_user(APPROVER)
		api.reject_attendance_correction_request(name, "打刻機の記録と合いません")
		frappe.set_user("Administrator")
		[row] = notifications(USER)
		self.assertEqual(row.notification_title, "修正申請が却下されました")
		self.assertEqual(row.message, "5月20日の出勤 9:03 · 理由は申請の詳細で確認してください")
		self.assertNotIn("打刻機", row.message)

	def test_apply_failure_sends_nothing_to_applicant(self, push):
		name = self.submit()
		frappe.set_user(APPROVER)
		with (
			patch.object(AttendanceCorrectionRequest, "apply_correction", side_effect=RuntimeError("boom")),
			patch.object(frappe.db, "commit"),
			self.assertRaises(frappe.ValidationError),
		):
			api.approve_attendance_correction_request(name)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Attendance Correction Request", name, "status"), "Apply Failed")
		self.assertEqual(notifications(USER), [])

	def test_same_account_gets_no_notification(self, push):
		frappe.db.set_value("Employee", self.employee, "attendance_correction_approver", USER)
		name = self.submit()
		self.assertEqual(notifications(USER), [])
		frappe.set_user(USER)
		api.reject_attendance_correction_request(name, "自分で取り下げ")
		frappe.set_user("Administrator")
		self.assertEqual(notifications(USER), [])

	def test_notification_failure_does_not_block_submit(self, push):
		with (
			patch("hrms.utils.correction_notifications._create", side_effect=RuntimeError("down")),
			patch.object(frappe, "log_error") as log_error,
		):
			name = self.submit()
		self.assertEqual(frappe.db.get_value("Attendance Correction Request", name, "status"), "Pending")
		log_error.assert_called_once()
