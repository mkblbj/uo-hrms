"""员工在 PWA 里查看、上传自己的头像。"""

import secrets

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms.utils.profile_photo import (
	MAX_UPLOAD_BYTES,
	PHOTO_FIELD,
	PHOTO_FILE_PREFIX,
	delete_photo_files,
	normalize_photo,
	photo_set_by_employee,
	sync_raven_profile_photo,
)


def get_current_employee():
	user = frappe.session.user
	employee = None
	if user != "Guest":
		employee = frappe.db.get_value(
			"Employee",
			{"user_id": user, "status": "Active"},
			["name", "image", "user_id"],
			as_dict=True,
		)
	if not employee:
		frappe.throw(_("No active employee is linked to your account."), frappe.PermissionError)
	return employee


@frappe.whitelist()
def get_profile_photo_status() -> dict:
	employee = get_current_employee()
	# 不用 get_single_value：空的日期会被转成 0001-01-01
	settings = frappe.get_cached_doc("HR Settings")
	deadline = (
		getdate(settings.get("profile_photo_deadline")) if settings.get("profile_photo_deadline") else None
	)
	own = photo_set_by_employee(employee)
	return {
		"required": bool(cint(settings.get("require_profile_photo"))),
		# 只有自己上传的才算设好；别人代设的头像照样提醒更换
		"has_photo": own,
		"temporary": bool(employee.image) and not own,
		"photo": employee.image or None,
		"deadline": str(deadline) if deadline else None,
		"overdue": bool(deadline) and getdate(today()) > deadline,
	}


@frappe.whitelist(methods=["POST"])
def upload_my_photo() -> dict:
	employee = get_current_employee()
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload:
		frappe.throw(_("Please choose a photo."))
	return save_employee_photo(employee, upload.stream.read(MAX_UPLOAD_BYTES + 1))


def save_employee_photo(employee, content: bytes) -> dict:
	"""处理照片，挂到员工的头像字段，同步账号头像，再删掉旧的头像文件。"""
	photo = normalize_photo(content)
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{PHOTO_FILE_PREFIX}{secrets.token_hex(10)}.jpg",
			"content": photo,
			"is_private": 0,
			"attached_to_doctype": "Employee",
			"attached_to_name": employee.name,
			"attached_to_field": PHOTO_FIELD,
		}
	).insert(ignore_permissions=True)

	frappe.db.set_value("Employee", employee.name, PHOTO_FIELD, file_doc.file_url)
	if employee.user_id:
		frappe.db.set_value("User", employee.user_id, "user_image", file_doc.file_url)
		frappe.clear_cache(user=employee.user_id)
		sync_raven_profile_photo(employee.user_id, file_doc.file_url)
	delete_photo_files(employee.name, employee.user_id, keep_url=file_doc.file_url, keep_name=file_doc.name)
	return {"photo": file_doc.file_url}
