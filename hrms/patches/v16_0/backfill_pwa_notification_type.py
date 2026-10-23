import frappe

SHIFT_REMINDER_TITLES = ("明日の勤務予定", "本日の勤務予定")
APPROVAL_DOCTYPES = ("Leave Application", "Expense Claim", "Shift Request")


def execute():
	"""给加类型之前的通知补上类型（可重复执行）；对象日期不补。

	加列时数据库会把已有的通知都填成默认值 Other，所以 Other 也当作还没分类、按规则重新判断；
	新代码写的 Other（端末登记等）不会命中下面任何一条规则，结果不变。
	"""
	notification = frappe.qb.DocType("PWA Notification")
	untyped = (
		notification.notification_type.isnull()
		| (notification.notification_type == "")
		| (notification.notification_type == "Other")
	)

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
