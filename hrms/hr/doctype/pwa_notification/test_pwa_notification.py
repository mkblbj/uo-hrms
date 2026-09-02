# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe

from hrms.hr.doctype.pwa_notification.pwa_notification import (
	get_permission_query_conditions,
	has_permission,
)
from hrms.tests.utils import HRMSTestSuite


class TestPWANotification(HRMSTestSuite):
	def test_explicit_title_and_route_are_used_for_push(self):
		doc = frappe.new_doc("PWA Notification")
		doc.to_user = "employee@example.com"
		doc.notification_title = "明日の勤務予定"
		doc.message = "明日（9月3日）は9:00〜18:00の勤務です。"
		doc.target_route = "/dashboard/work-roster?view=mine"
		push = MagicMock()
		push.is_enabled.return_value = True

		with (
			patch("frappe.push_notification.PushNotification", return_value=push),
			patch("frappe.utils.get_url", return_value="https://hr.example.test"),
		):
			doc.send_push_notification()

		push.send_notification_to_user.assert_called_once_with(
			"employee@example.com",
			"明日の勤務予定",
			doc.message,
			link="https://hr.example.test/hrms/dashboard/work-roster?view=mine",
			icon="https://hr.example.test/assets/hrms/manifest/favicon-196.png",
		)

	def test_disabled_push_still_allows_application_notification(self):
		push = MagicMock()
		push.is_enabled.return_value = False
		with patch("frappe.push_notification.PushNotification", return_value=push):
			doc = frappe.get_doc(
				{
					"doctype": "PWA Notification",
					"to_user": "Administrator",
					"notification_title": "明日の勤務予定",
					"message": "明日は勤務です。",
				}
			).insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("PWA Notification", doc.name))
		push.send_notification_to_user.assert_not_called()

	def test_employee_can_read_only_own_notifications(self):
		with patch(
			"hrms.hr.doctype.pwa_notification.pwa_notification.frappe.get_roles",
			return_value=["Employee"],
		):
			condition = get_permission_query_conditions("employee@example.com")
			self.assertIn("to_user", condition)
			self.assertTrue(
				has_permission(
					frappe._dict(to_user="employee@example.com"),
					"employee@example.com",
					"read",
				)
			)
			self.assertFalse(
				has_permission(
					frappe._dict(to_user="other@example.com"),
					"employee@example.com",
					"read",
				)
			)

	def test_target_route_must_resolve_within_hrms(self):
		for target_route in (
			"dashboard/work-roster",
			"//example.com",
			"/../logout",
			"/%2e%2e/logout",
			"/%2e%2e?next=/logout",
			"/%2e%2e#logout",
		):
			with self.assertRaises(frappe.ValidationError):
				frappe.get_doc(
					{
						"doctype": "PWA Notification",
						"to_user": "Administrator",
						"message": "明日は勤務です。",
						"target_route": target_route,
					}
				).insert(ignore_permissions=True)
