"""受开放开关和试用名单控制的 PWA 本人资料收集。"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, validate_email_address

EMERGENCY_FIELDS = ("person_to_be_contacted", "relation", "emergency_phone_number")
CONTACT_FIELDS = {"cell_number", "custom_wechat_id", "current_address", "contact_email", *EMERGENCY_FIELDS}


def _eligible_employee():
	user = frappe.session.user
	users = frappe.conf.get("pwa_profile_collection_users")
	enabled_for_all = cint(frappe.conf.get("pwa_profile_collection_enabled")) == 1
	in_pilot = isinstance(users, list) and user in users
	if user == "Guest" or not (enabled_for_all or in_pilot):
		return None
	if not frappe.db.get_value("User", user, "enabled"):
		return None
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _my_employee():
	name = _eligible_employee()
	if not name:
		frappe.throw(_("Profile collection is not enabled for your account."), frappe.PermissionError)
	doc = frappe.get_doc("Employee", name)
	if doc.user_id != frappe.session.user or doc.status != "Active":
		frappe.throw(_("Profile collection is not enabled for your account."), frappe.PermissionError)
	return doc


def _profile(doc):
	account_email = cstr(doc.user_id).strip()
	return {
		"employee": doc.name,
		"employee_name": doc.employee_name,
		"employee_number": doc.employee_number or doc.name,
		"cell_number": doc.cell_number or "",
		"custom_wechat_id": doc.get("custom_wechat_id") or "",
		"current_address": doc.current_address or "",
		**{field: doc.get(field) or "" for field in EMERGENCY_FIELDS},
		"contact_email": cstr(doc.company_email).strip()
		or cstr(doc.personal_email).strip()
		or (account_email if "@" in account_email else ""),
		"modified": cstr(doc.modified),
	}


@frappe.whitelist()
def get_collection_status():
	return {"enabled": bool(_eligible_employee())}


@frappe.whitelist()
def get_my_profile():
	return _profile(_my_employee())


@frappe.whitelist(methods=["POST"])
def save_my_profile(profile: dict | str):
	doc = _my_employee()
	try:
		profile = frappe.parse_json(profile)
	except (ValueError, TypeError):
		frappe.throw(_("Invalid profile data."))
	if not isinstance(profile, dict) or set(profile) != CONTACT_FIELDS | {"modified"}:
		frappe.throw(_("Invalid profile data."))
	values = {}
	for field in CONTACT_FIELDS:
		value = profile[field]
		if not isinstance(value, str):
			frappe.throw(_("Invalid profile data."))
		values[field] = value.strip()
	if not values["cell_number"] or not values["current_address"] or not values["contact_email"]:
		frappe.throw(_("Mobile, current address and contact email are required."))
	if any(not values[field] for field in EMERGENCY_FIELDS):
		frappe.throw(_("Emergency contact name, relationship and phone number are required."))
	validate_email_address(values["contact_email"], throw=True)
	if not isinstance(profile["modified"], str) or profile["modified"] != cstr(doc.modified):
		frappe.throw(
			_("Your profile was updated elsewhere. Reload it before submitting again."),
			frappe.TimestampMismatchError,
		)
	doc.cell_number = values["cell_number"]
	doc.custom_wechat_id = values["custom_wechat_id"]
	doc.current_address = values["current_address"]
	for field in EMERGENCY_FIELDS:
		doc.set(field, values[field])
	email_field = "company_email" if cstr(doc.company_email).strip() else "personal_email"
	doc.set(email_field, values["contact_email"])
	# 会话、名单和本人归属已在上方核验；只保存这里固定的联系字段。
	# 常规 save 继续执行 Employee 校验、版本冲突检查及原有更新事件。
	doc.save(ignore_permissions=True)
	return _profile(doc)
