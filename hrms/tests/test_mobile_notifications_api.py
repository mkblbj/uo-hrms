"""App 的通知列表、详情、已读（S6），以及点开后去哪个画面。"""

from datetime import datetime, timedelta
from unittest.mock import patch

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import mobile
from hrms.tests.test_mobile_correction_api import make_request
from hrms.tests.test_mobile_roster_api import HOLIDAY_LIST, YEAR, ensure_department, ensure_period
from hrms.tests.utils import HRMSTestSuite
from hrms.utils import mobile_notifications

USER = "mobile-notice@example.com"
OTHER_USER = "mobile-notice-other@example.com"
NOW = datetime(2031, 10, 20, 10, 0)


def ensure_holiday_list():
	if frappe.db.exists("Holiday List", HOLIDAY_LIST):
		return
	frappe.get_doc(
		{
			"doctype": "Holiday List",
			"holiday_list_name": HOLIDAY_LIST,
			"from_date": f"{YEAR}-01-01",
			"to_date": f"{YEAR}-12-31",
		}
	).insert(ignore_permissions=True)


class NotificationApiTestCase(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.office = ensure_department("Mobile Roster Office", "Office")
		self.employee = make_employee(USER, company="_Test Company")
		make_employee(OTHER_USER, company="_Test Company")
		frappe.db.set_value("Employee", self.employee, {"department": self.office, "status": "Active"})
		for user in (USER, OTHER_USER):
			frappe.get_doc("User", user).add_roles("Employee")
		frappe.db.delete("PWA Notification", {"to_user": ["in", [USER, OTHER_USER]]})
		self.minutes = 0

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def notify(self, user=USER, minutes_ago=None, read=0, **values):
		"""插一条通知；creation 依次往前推，最先插的最新。"""
		self.minutes += 10
		doc = frappe.get_doc(
			{
				"doctype": "PWA Notification",
				"from_user": "Administrator",
				"to_user": user,
				"message": "お知らせです。",
				**values,
			}
		)
		doc.flags.defer_push_notification = True
		doc.insert(ignore_permissions=True)
		creation = NOW - timedelta(minutes=minutes_ago if minutes_ago is not None else self.minutes)
		frappe.db.set_value("PWA Notification", doc.name, {"creation": creation, "read": read}, update_modified=False)
		return str(doc.name)


class TestNotificationTargets(NotificationApiTestCase):
	def target_of(self, **values):
		name = self.notify(**values)
		row = frappe.db.get_value("PWA Notification", name, mobile_notifications.FIELDS, as_dict=True)
		return mobile_notifications.target(row, USER)

	def test_every_screen(self):
		ensure_holiday_list()
		production = ensure_department("Mobile Roster Production", "Production")
		self.assertTrue(production)
		office_nov = ensure_period("Office", 11, "Collecting", deadline=f"{YEAR}-10-23")
		production_nov = ensure_period("Production", 11, "Collecting", deadline=f"{YEAR}-10-23")
		office_oct = ensure_period("Office", 10, "Published")
		frappe.db.set_value("Employee", self.employee, "attendance_correction_approver", OTHER_USER)
		request = make_request(self.employee, "2026-05-20")

		cases = [
			(
				{"notification_type": "Approval", "reference_document_type": "Attendance Correction Request", "reference_document_name": request.name},
				{"screen": "correction", "name": request.name},
			),
			(
				{"notification_type": "Approval", "reference_document_type": "Attendance Correction Request", "reference_document_name": "HR-ACR-GONE"},
				{"screen": "notification"},
			),
			(
				{"notification_type": "Announcement", "reference_document_type": "WR Period", "reference_document_name": office_nov},
				{"screen": "preference", "period": office_nov},
			),
			(
				{"notification_type": "Announcement", "reference_document_type": "WR Period", "reference_document_name": production_nov},
				{"screen": "roster", "date": f"{YEAR}-11-01"},
			),
			(
				{"notification_type": "Announcement", "reference_document_type": "WR Period", "reference_document_name": office_oct},
				{"screen": "roster", "date": f"{YEAR}-10-01"},
			),
			({"notification_type": "Shift Reminder", "reference_date": "2031-10-21"}, {"screen": "roster", "date": "2031-10-21"}),
			({"notification_type": "Shift Change"}, {"screen": "roster", "date": None}),
			({"notification_type": "Announcement"}, {"screen": "notification"}),
			({"notification_type": "Other"}, {"screen": "notification"}),
			({"notification_type": "Approval", "reference_document_type": "Leave Application", "reference_document_name": "X"}, {"screen": "notification"}),
		]
		for values, expected in cases:
			with self.subTest(values):
				self.assertEqual(self.target_of(**values), expected)


class TestNotificationList(NotificationApiTestCase):
	def test_items_are_mine_newest_first(self):
		first = self.notify(notification_title="明日の勤務予定", notification_type="Shift Reminder", reference_date="2031-10-21")
		second = self.notify(notification_type="Announcement", message="<p>健康診断&amp;説明会</p><p>本社 3階</p>", read=1)
		self.notify(user=OTHER_USER)
		frappe.set_user(USER)
		with patch.object(mobile, "now_datetime", return_value=NOW):
			result = mobile.get_notifications()
		self.assertEqual(result["api_version"], 1)
		self.assertEqual(result["today"], "2031-10-20")
		self.assertEqual(result["unread_count"], 1)
		self.assertFalse(result["has_more"])
		self.assertEqual(
			result["items"],
			[
				{
					"name": first,
					"type": "shift_reminder",
					"title": "明日の勤務予定",
					"body": "お知らせです。",
					"creation": "2031-10-20 09:50:00",
					"read": False,
					"target": {"screen": "roster", "date": "2031-10-21"},
				},
				{
					"name": second,
					"type": "announcement",
					"title": None,
					"body": "健康診断&説明会 本社 3階",
					"creation": "2031-10-20 09:40:00",
					"read": True,
					"target": {"screen": "notification"},
				},
			],
		)

	def test_category_filters_items_but_not_unread_count(self):
		reminder = self.notify(notification_type="Shift Reminder")
		change = self.notify(notification_type="Shift Change")
		approval = self.notify(notification_type="Approval")
		announcement = self.notify(notification_type="Announcement")
		self.notify(notification_type="Other")
		frappe.set_user(USER)
		expected = {
			"shift": [reminder, change],
			"approval": [approval],
			"announcement": [announcement],
		}
		for category, names in expected.items():
			with self.subTest(category):
				result = mobile.get_notifications(category=category)
				self.assertEqual([item["name"] for item in result["items"]], names)
				self.assertEqual(result["unread_count"], 5)
		self.assertEqual(len(mobile.get_notifications()["items"]), 5)

	def test_paging_with_before(self):
		names = [self.notify() for _ in range(5)]
		# 同一时刻的两条按编号排
		frappe.db.set_value("PWA Notification", names[3], "creation", frappe.db.get_value("PWA Notification", names[2], "creation"), update_modified=False)
		frappe.set_user(USER)
		page = mobile.get_notifications(limit="2")
		self.assertTrue(page["has_more"])
		self.assertEqual([item["name"] for item in page["items"]], names[:2])
		page = mobile.get_notifications(limit="2", before=names[1])
		self.assertTrue(page["has_more"])
		self.assertEqual([item["name"] for item in page["items"]], [names[3], names[2]])
		page = mobile.get_notifications(limit="2", before=names[2])
		self.assertFalse(page["has_more"])
		self.assertEqual([item["name"] for item in page["items"]], [names[4]])

	def test_body_is_cut_to_300(self):
		self.notify(message="あ" * 400)
		frappe.set_user(USER)
		body = mobile.get_notifications()["items"][0]["body"]
		self.assertEqual(len(body), 300)
		self.assertTrue(body.endswith("…"))

	def test_invalid_params_are_417(self):
		other = self.notify(user=OTHER_USER)
		frappe.set_user(USER)
		for params in (
			{"category": "other"},
			{"limit": "0"},
			{"limit": "101"},
			{"limit": "ten"},
			{"before": "abc"},
			{"before": other},
			{"before": "999999999"},
		):
			with self.subTest(params), self.assertRaises(frappe.ValidationError):
				mobile.get_notifications(**params)

	def test_empty(self):
		frappe.set_user(USER)
		result = mobile.get_notifications()
		self.assertEqual((result["items"], result["unread_count"], result["has_more"]), ([], 0, False))

	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			mobile.get_notifications()


class TestNotificationDetail(NotificationApiTestCase):
	def test_detail_has_full_body_and_clean_html(self):
		html = (
			'<p>年末調整の書類は<a href="https://example.com/form">こちら</a>から。</p>'
			"<script>alert(1)</script>" + "<p>" + "い" * 400 + "</p>"
		)
		name = self.notify(notification_type="Announcement", notification_title="年末調整", use_html_source=1, html_source=html)
		frappe.set_user(USER)
		detail = mobile.get_notification(name)
		self.assertEqual(detail["name"], name)
		self.assertEqual(detail["title"], "年末調整")
		self.assertTrue(detail["body"].startswith("年末調整の書類はこちらから。"))
		self.assertEqual(len(detail["body"]), len("年末調整の書類はこちらから。") + 1 + 400)
		self.assertIn('href="https://example.com/form"', detail["message_html"])
		self.assertNotIn("<script", detail["message_html"])
		self.assertFalse(detail["read"])
		self.assertEqual(frappe.db.get_value("PWA Notification", name, "read"), 0)

	def test_missing_or_others_are_417(self):
		other = self.notify(user=OTHER_USER)
		frappe.set_user(USER)
		for name in (other, "999999999", "abc", None):
			with self.subTest(name), self.assertRaisesRegex(frappe.ValidationError, "Notification not found"):
				mobile.get_notification(name)


class TestMarkRead(NotificationApiTestCase):
	def test_mark_names(self):
		a, b, c = self.notify(), self.notify(), self.notify()
		other = self.notify(user=OTHER_USER)
		modified = frappe.db.get_value("PWA Notification", a, "modified")
		frappe.set_user(USER)
		with patch("hrms.refetch_resource") as refetch:
			result = mobile.mark_notifications_read(names=[a, b, other, "999999999", "abc"])
		self.assertEqual(result, {"unread_count": 1})
		refetch.assert_called_once_with("hrms:notifications", USER)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("PWA Notification", a, "read"), 1)
		self.assertEqual(frappe.db.get_value("PWA Notification", c, "read"), 0)
		self.assertEqual(frappe.db.get_value("PWA Notification", other, "read"), 0)
		self.assertEqual(frappe.db.get_value("PWA Notification", a, "modified"), modified)

	def test_mark_all_and_json_string(self):
		a = self.notify()
		self.notify()
		other = self.notify(user=OTHER_USER)
		frappe.set_user(USER)
		self.assertEqual(mobile.mark_notifications_read(names=f'["{a}"]'), {"unread_count": 1})
		self.assertEqual(mobile.mark_notifications_read(all=True), {"unread_count": 0})
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("PWA Notification", other, "read"), 0)

	def test_needs_exactly_one_of_names_or_all(self):
		a = self.notify()
		frappe.set_user(USER)
		for params in ({}, {"names": [a], "all": True}, {"all": False}, {"names": [str(i) for i in range(101)]}, {"names": "x"}):
			with self.subTest(params), self.assertRaises(frappe.ValidationError):
				mobile.mark_notifications_read(**params)
