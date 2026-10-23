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


class TestPWANotificationType(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()

	def insert(self, **values):
		doc = frappe.get_doc({"doctype": "PWA Notification", "to_user": "Administrator", **values})
		doc.flags.defer_push_notification = True
		return doc.insert(ignore_permissions=True)

	def test_type_defaults_to_other(self):
		self.assertEqual(self.insert(message="x").notification_type, "Other")
		self.assertEqual(self.insert(message="x", notification_type="").notification_type, "Other")
		doc = self.insert(message="x", notification_type="Approval", reference_date="2026-10-16")
		self.assertEqual((doc.notification_type, str(doc.reference_date)), ("Approval", "2026-10-16"))

	@patch.object(PWANotification, "send_push_notification")
	def test_group_copies_carry_title_and_type(self, _push):
		parent = frappe.new_doc("PWA Notification")
		parent.notification_title = "健康診断のお知らせ"
		parent.message = "<p>11月に実施します。</p>"
		parent.notification_type = "Announcement"
		parent._create_notification_for_user("Administrator")
		copy = frappe.get_last_doc("PWA Notification", filters={"to_user": "Administrator"})
		self.assertEqual(copy.notification_title, "健康診断のお知らせ")
		self.assertEqual(copy.notification_type, "Announcement")

		parent.notification_type = None
		parent._create_notification_for_user("Administrator")
		copy = frappe.get_last_doc("PWA Notification", filters={"to_user": "Administrator"})
		self.assertEqual(copy.notification_type, "Announcement")

	@patch.object(PWANotification, "send_push_notification")
	def test_approval_mixin_writes_approval_type(self, _push):
		from hrms.mixins.pwa_notifications import PWANotificationsMixin

		class FakeLeave(frappe._dict, PWANotificationsMixin):
			def _get_employee_user(self):
				return "Administrator"

		FakeLeave(
			doctype="Leave Application", name="HR-LAP-TEST", employee_name="テスト", leave_approver="Guest"
		).notify_approver()
		notification = frappe.get_last_doc("PWA Notification", filters={"to_user": "Guest"})
		self.assertEqual(notification.notification_type, "Approval")
		self.assertEqual(notification.reference_document_type, "Leave Application")

	@patch.object(PWANotification, "send_push_notification")
	def test_device_registration_notices_are_other(self, _push):
		from hrms.api.device_key import _notify_key_registered
		from hrms.api.passkey import _notify_new_device

		_notify_new_device("Administrator", "Chrome")
		self.assertEqual(
			frappe.get_last_doc("PWA Notification", filters={"to_user": "Administrator"}).notification_type,
			"Other",
		)
		_notify_key_registered("Administrator", "iPhone")
		self.assertEqual(
			frappe.get_last_doc("PWA Notification", filters={"to_user": "Administrator"}).notification_type,
			"Other",
		)

	@patch.object(PWANotification, "send_push_notification")
	def test_send_announcement_is_announcement(self, _push):
		from hrms import send_announcement

		with patch.object(frappe.db, "commit"), patch("builtins.print"):
			send_announcement.send_to_user("Administrator", "全社停電のお知らせ")
		notification = frappe.get_last_doc("PWA Notification", filters={"to_user": "Administrator"})
		self.assertEqual(notification.notification_type, "Announcement")

	def test_backfill_patch_sets_types_by_title_and_reference(self):
		from hrms.patches.v16_0.backfill_pwa_notification_type import execute

		cases = {
			"Shift Reminder": [{"notification_title": "明日の勤務予定"}, {"notification_title": "本日の勤務予定"}],
			"Shift Change": [{"notification_title": "勤務予定が変更されました"}],
			"Announcement": [{"reference_document_type": "WR Period", "reference_document_name": "Office-2026-11"}],
			"Approval": [
				{"reference_document_type": doctype, "reference_document_name": "X"}
				for doctype in ("Leave Application", "Expense Claim", "Shift Request")
			],
			"Other": [{"notification_title": "顔認証打刻の端末が登録されました"}, {}],
		}
		names = {}
		for expected, rows in cases.items():
			for index, values in enumerate(rows):
				doc = self.insert(message="x", **values)
				# 加列时已有的通知会被填成默认值 Other；也覆盖空值
				old_value = None if index % 2 else "Other"
				frappe.db.set_value("PWA Notification", doc.name, "notification_type", old_value, update_modified=False)
				names[doc.name] = expected
		kept = self.insert(message="x", notification_title="明日の勤務予定", notification_type="Announcement")
		device_notice = self.insert(
			message="x", notification_title="顔認証打刻の端末が登録されました", notification_type="Other"
		)

		execute()
		execute()

		for name, expected in names.items():
			self.assertEqual(frappe.db.get_value("PWA Notification", name, "notification_type"), expected, name)
		self.assertEqual(frappe.db.get_value("PWA Notification", kept.name, "notification_type"), "Announcement")
		self.assertEqual(frappe.db.get_value("PWA Notification", device_notice.name, "notification_type"), "Other")
