import frappe

SHIFT_REMINDER_TITLES = ("明日の勤務予定", "本日の勤務予定")
APPROVAL_DOCTYPES = ("Leave Application", "Expense Claim", "Shift Request")


def execute():
	"""给加类型之前的通知补上类型（只补空的，可重复执行）；对象日期不补。"""
	notification = frappe.qb.DocType("PWA Notification")
	untyped = (notification.notification_type.isnull()) | (notification.notification_type == "")

	def fill(notification_type, condition):
		(
			frappe.qb.update(notification)
			.set(notification.notification_type, notification_type)
			.where(untyped & condition)
		).run()

	fill("Shift Reminder", notification.notification_title.isin(SHIFT_REMINDER_TITLES))
	fill("Shift Change", notification.notification_title.like("勤務予定が%"))
	fill("Announcement", notification.reference_document_type == "WR Period")
	fill("Approval", notification.reference_document_type.isin(APPROVAL_DOCTYPES))
	fill("Other", notification.name.isnotnull())
