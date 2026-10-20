"""补卡申请的通知：提交后告诉审批人，批准 / 驳回后告诉申请人。

文字只写日文、不写理由（理由可能涉及个人情况，推送会出现在锁屏上）。事务提交后才推送，回滚了的不推。
"""

import frappe
from frappe.utils import escape_html, get_datetime, getdate

DOCTYPE = "Attendance Correction Request"
LOG_LABELS = {"IN": "出勤", "OUT": "退勤"}
SAVEPOINT = "attendance_correction_notification"


def notify_status_change(doc) -> None:
	before = doc.get_doc_before_save()
	old_status = before.status if before else None
	if doc.status == old_status:
		return
	frappe.db.savepoint(SAVEPOINT)
	try:
		if doc.status == "Pending":
			_notify_submitted(doc)
		elif doc.status in ("Applied", "Rejected"):
			_notify_decided(doc)
	except Exception:
		# 通知失败不能挡住提交和审批
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(f"Attendance correction notification failed: {doc.name}")
	finally:
		frappe.db.release_savepoint(SAVEPOINT)


def _notify_submitted(doc) -> None:
	applicant = _applicant_user(doc)
	if not doc.approver or doc.approver == applicant:
		return
	_create(
		doc,
		to_user=doc.approver,
		from_user=applicant or frappe.session.user,
		title="修正申請が届きました",
		message=f"{escape_html(doc.employee_name or doc.employee)}さん · {_what(doc)}",
	)


def _notify_decided(doc) -> None:
	applicant = _applicant_user(doc)
	operator = doc.approved_by or frappe.session.user
	if not applicant or applicant == operator:
		return
	if doc.status == "Applied":
		title, message = "修正申請が承認されました", f"{_what(doc)} {_when(doc)}"
	else:
		title = "修正申請が却下されました"
		message = f"{_what(doc)} {_when(doc)} · 理由は申請の詳細で確認してください"
	_create(doc, to_user=applicant, from_user=operator, title=title, message=message)


def _create(doc, *, to_user: str, from_user: str, title: str, message: str) -> None:
	notification = frappe.get_doc(
		{
			"doctype": "PWA Notification",
			"from_user": from_user,
			"to_user": to_user,
			"notification_title": title,
			"notification_type": "Approval",
			"message": message,
			"reference_document_type": DOCTYPE,
			"reference_document_name": doc.name,
			"reference_date": doc.attendance_date,
			"target_route": f"/attendance-corrections/{doc.name}",
		}
	)
	notification.flags.defer_push_notification = True
	notification.insert(ignore_permissions=True)
	frappe.db.after_commit.add(notification.send_push_notification)


def _applicant_user(doc) -> str | None:
	return frappe.db.get_value("Employee", doc.employee, "user_id")


def _what(doc) -> str:
	day = getdate(doc.attendance_date)
	return f"{day.month}月{day.day}日の{LOG_LABELS.get(doc.requested_log_type, '打刻')}"


def _when(doc) -> str:
	time = get_datetime(doc.requested_time)
	return f"{time.hour}:{time.minute:02d}"
