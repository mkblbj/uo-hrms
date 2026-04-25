# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document

import hrms


class PWANotification(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_user: DF.Link | None
		message: DF.TextEditor | None
		name: DF.Int | None
		read: DF.Check
		reference_document_name: DF.Data | None
		reference_document_type: DF.Link | None
		to_user: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		# 默认来源用户为当前登录用户
		if not self.from_user:
			self.from_user = frappe.session.user
		
		# 群发处理
		if self.send_to_all:
			self.send_to_all_employees()
			frappe.throw(
				frappe._("通知已成功发送给所有员工！"),
				frappe.ValidationError,
				title=frappe._("发送成功")
			)
		
		# 多选用户处理
		if self.recipients and len(self.recipients) > 0:
			self.send_to_multiple_users()
			frappe.throw(
				frappe._("通知已成功发送给选中的用户！"),
				frappe.ValidationError,
				title=frappe._("发送成功")
			)
	
	def send_to_all_employees(self):
		"""发送通知给所有有 User 账号的员工"""
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active", "user_id": ["is", "set"]},
			pluck="user_id"
		)
		
		for user_id in employees:
			if user_id:
				self._create_notification_for_user(user_id)
		
		frappe.db.commit()
		frappe.msgprint(f"已成功发送通知给 {len(employees)} 位员工")
	
	def send_to_multiple_users(self):
		"""发送通知给多个选中的用户"""
		count = 0
		for recipient in self.recipients:
			if recipient.user:
				self._create_notification_for_user(recipient.user)
				count += 1
		
		frappe.db.commit()
		frappe.msgprint(f"已成功发送通知给 {count} 位用户")
	
	def _create_notification_for_user(self, user_id):
		"""创建单个用户的通知"""
		notification = frappe.new_doc("PWA Notification")
		notification.from_user = self.from_user or frappe.session.user
		notification.to_user = user_id
		notification.message = self.message
		notification.use_html_source = self.use_html_source
		notification.html_source = self.html_source
		notification.reference_document_type = self.reference_document_type
		notification.reference_document_name = self.reference_document_name
		notification.send_to_all = 0
		notification.flags.ignore_permissions = True
		notification.insert()
	
	def get_display_message(self):
		"""获取实际要显示的消息内容"""
		if self.use_html_source and self.html_source:
			return self.html_source
		return self.message

	def on_update(self):
		hrms.refetch_resource("hrms:notifications", self.to_user)

	def after_insert(self):
		self.send_push_notification()

	def send_push_notification(self):
		try:
			from frappe.push_notification import PushNotification

			push_notification = PushNotification("hrms")
			if push_notification.is_enabled():
				push_notification.send_notification_to_user(
					self.to_user,
					self.reference_document_type,
					self.message,
					link=self.get_notification_link(),
					icon=f"{frappe.utils.get_url()}/assets/hrms/manifest/favicon-196.png",
				)
		except ImportError:
			# push notifications are not supported in the current framework version
			pass
		except Exception:
			self.log_error(f"Error sending push notification: {self.name}")

	def get_notification_link(self):
		base_url = f"{frappe.utils.get_url()}/hrms"

		if self.reference_document_type == "Leave Application":
			return f"{base_url}/leave-applications/{self.reference_document_name}"
		elif self.reference_document_type == "Expense Claim":
			return f"{base_url}/expense-claims/{self.reference_document_name}"

		return base_url
