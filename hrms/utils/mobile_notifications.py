"""原生 App 的通知规则：类型、纯文本正文、点开后去哪个画面、推送开关。APNs 推送和通知接口共用。"""

import re

from bs4 import BeautifulSoup

import frappe

DOCTYPE = "PWA Notification"
SETTINGS_DOCTYPE = "Mobile Push Settings"
CORRECTION_DOCTYPE = "Attendance Correction Request"
PERIOD_DOCTYPE = "WR Period"

TYPE_KEYS = {
	"Shift Reminder": "shift_reminder",
	"Shift Change": "shift_change",
	"Approval": "approval",
	"Announcement": "announcement",
	"Other": "other",
}
# 「其他」没有开关（端末登记这类安全提醒总是推送）
SWITCH_KEYS = ("shift_reminder", "shift_change", "approval", "announcement")
SHIFT_KEYS = ("shift_reminder", "shift_change")
DEFAULT_TITLES = {
	"shift_reminder": "明日のシフト",
	"shift_change": "シフトの変更",
	"approval": "申請・承認",
	"announcement": "会社からのお知らせ",
	"other": "お知らせ",
}
FIELDS = (
	"name",
	"to_user",
	"notification_title",
	"notification_type",
	"message",
	"use_html_source",
	"html_source",
	"read",
	"creation",
	"reference_document_type",
	"reference_document_name",
	"reference_date",
)
_BLOCK_TAGS = ("p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre")


def type_key(notification_type: str | None) -> str:
	return TYPE_KEYS.get(notification_type or "", "other")


def display_html(row) -> str:
	"""PWA 实际显示的内容：开了 HTML 源代码模式用 html_source，否则用 message。"""
	if row.get("use_html_source") and row.get("html_source"):
		return row.get("html_source")
	return row.get("message") or ""


def plain_text(html: str | None, limit: int | None = None) -> str:
	"""去掉 HTML、合并空白；超过 limit 时截断，结果连「…」在内不超过 limit 个字。"""
	soup = BeautifulSoup(html or "", "html.parser")
	for tag in soup(["script", "style"]):
		tag.decompose()
	for tag in soup.find_all("br"):
		tag.replace_with("\n")
	for tag in soup.find_all(_BLOCK_TAGS):
		tag.append("\n")
	# 行内标签之间不加空格，日文才不会被拆开
	text = re.sub(r"\s+", " ", soup.get_text("")).strip()
	if limit and len(text) > limit:
		text = text[: limit - 1].rstrip() + "…"
	return text


def targets(rows: list, user: str) -> list[dict]:
	"""每条通知点开后去哪里（App 和推送用同一套）。"""
	correction_names = {
		row.reference_document_name
		for row in rows
		if row.reference_document_type == CORRECTION_DOCTYPE and row.reference_document_name
	}
	existing_corrections = (
		set(frappe.get_all(CORRECTION_DOCTYPE, filters={"name": ["in", list(correction_names)]}, pluck="name"))
		if correction_names
		else set()
	)
	period_names = {
		row.reference_document_name
		for row in rows
		if row.reference_document_type == PERIOD_DOCTYPE and row.reference_document_name
	}
	periods = (
		{
			period.name: period
			for period in frappe.get_all(
				PERIOD_DOCTYPE,
				filters={"name": ["in", list(period_names)]},
				fields=["name", "status", "department_category", "year", "month"],
			)
		}
		if period_names and "work_roster" in frappe.get_installed_apps()
		else {}
	)
	category = _user_category(user) if periods else None
	return [_target(row, existing_corrections, periods, category) for row in rows]


def target(row, user: str) -> dict:
	return targets([row], user)[0]


def _target(row, existing_corrections: set, periods: dict, category: str | None) -> dict:
	name = row.reference_document_name
	if row.reference_document_type == CORRECTION_DOCTYPE and name in existing_corrections:
		return {"screen": "correction", "name": name}
	if row.reference_document_type == PERIOD_DOCTYPE and (period := periods.get(name)):
		if period.status == "Collecting" and period.department_category == category:
			return {"screen": "preference", "period": period.name}
		return {"screen": "roster", "date": f"{int(period.year):04d}-{int(period.month):02d}-01"}
	if type_key(row.notification_type) in SHIFT_KEYS:
		return {"screen": "roster", "date": str(row.reference_date) if row.reference_date else None}
	return {"screen": "notification"}


def _user_category(user: str) -> str | None:
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	if not employee:
		return None
	from work_roster.api.schedule import _get_employee_department_category

	return _get_employee_department_category(employee)


def push_settings(user: str) -> dict[str, bool]:
	"""四类推送开关；没有记录就是全开。"""
	row = frappe.db.get_value(SETTINGS_DOCTYPE, user, SWITCH_KEYS, as_dict=True)
	return {key: bool(row[key]) if row else True for key in SWITCH_KEYS}


def push_allowed(user: str, kind: str) -> bool:
	return kind == "other" or push_settings(user).get(kind, True)


def unread_count(user: str) -> int:
	return frappe.db.count(DOCTYPE, {"to_user": user, "read": 0})
