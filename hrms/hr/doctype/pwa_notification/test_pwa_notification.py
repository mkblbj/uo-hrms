# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import IntegrationTestCase

from hrms.hr.doctype.pwa_notification.pwa_notification import (
	PWANotification,
	get_permission_query_conditions,
)

IGNORE_TEST_RECORD_DEPENDENCIES = ["User", "DocType"]


class TestPWANotification(IntegrationTestCase):
	@patch.object(PWANotification, "send_push_notification")
	def test_defer_push_flag_only_skips_deferred_insert(self, send_push):
		deferred = frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"to_user": "Administrator",
				"message": "Deferred push",
			}
		)
		deferred.flags.defer_push_notification = True

		deferred.insert(ignore_permissions=True)

		send_push.assert_not_called()

		frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"to_user": "Administrator",
				"message": "Immediate push",
			}
		).insert(ignore_permissions=True)

		send_push.assert_called_once_with()

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

	def test_document_read_permission_uses_recipient_and_manager_roles(self):
		doc = frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"to_user": "employee@example.com",
				"message": "明日は勤務です。",
			}
		)
		roles = {
			"employee@example.com": ["Employee"],
			"other@example.com": ["Employee"],
			"hr-manager@example.com": ["HR Manager"],
			"system-manager@example.com": ["System Manager"],
		}

		with patch.object(
			frappe,
			"get_roles",
			side_effect=lambda user=None: roles[user or frappe.session.user],
		):
			condition = get_permission_query_conditions("employee@example.com")
			self.assertIn("to_user", condition)
			self.assertTrue(
				frappe.has_permission(
					"PWA Notification",
					ptype="read",
					doc=doc,
					user="employee@example.com",
				)
			)
			self.assertFalse(
				frappe.has_permission(
					"PWA Notification",
					ptype="read",
					doc=doc,
					user="other@example.com",
				)
			)
			for manager in (
				"hr-manager@example.com",
				"system-manager@example.com",
			):
				with self.subTest(manager=manager):
					self.assertTrue(
						frappe.has_permission(
							"PWA Notification",
							ptype="read",
							doc=doc,
							user=manager,
						)
					)

	def test_target_route_must_resolve_within_hrms(self):
		for target_route in (
			"dashboard/work-roster",
			"//example.com",
			"/../logout",
			"/..\\logout",
			"/%2e%2e/logout",
			"/%2e%2e%5clogout",
			"/%2e%2e?next=/logout",
			"/%2e%2e#logout",
			"/dashboard/%00logout",
			"/dashboard/\x1flogout",
		):
			with self.subTest(target_route=repr(target_route)):
				with self.assertRaises(frappe.ValidationError):
					frappe.get_doc(
						{
							"doctype": "PWA Notification",
							"to_user": "Administrator",
							"message": "明日は勤務です。",
							"target_route": target_route,
						}
					).insert(ignore_permissions=True)

	def test_target_route_is_unchanged_and_validated_on_update(self):
		doc = frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"to_user": "Administrator",
				"message": "明日は勤務です。",
				"target_route": "/dashboard/work-roster?view=mine",
			}
		)
		doc.flags.defer_push_notification = True
		doc.insert(ignore_permissions=True)
		self.assertEqual(
			doc.target_route,
			"/dashboard/work-roster?view=mine",
		)

		doc.target_route = "/..\\logout"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)
