# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

"""面容/指纹（通行密钥）打卡接口：设置、首页一键打卡、门口 NFC 页。"""

import json

from webauthn.helpers import bytes_to_base64url

import frappe
from frappe import _
from frappe.utils import cint, now

from hrms.api.checkin_presence import EVIDENCE_GPS, evaluate_presence
from hrms.api.checkin_service import (
	CHECKIN_METHOD_NFC_PASSKEY,
	CHECKIN_METHOD_PASSKEY,
	create_checkin,
	resolve_auto_log_type,
	validate_checkin_timing,
)
from hrms.api.passkey_webauthn import (
	PURPOSE_CHECKIN,
	PURPOSE_NFC,
	PURPOSE_REGISTER,
	PasskeyVerificationError,
	build_authentication_options,
	build_registration_options,
	extract_client_challenge,
	pop_challenge,
	verify_assertion,
	verify_registration,
)
from hrms.utils.client_network import get_client_ip, is_office_network

MAX_PASSKEYS_PER_EMPLOYEE = 3
VALID_LOG_TYPES = ("IN", "OUT")


def _require_employee_user():
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		frappe.throw(_("Please login first"), frappe.PermissionError)
	employee = frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"}, ["name", "employee_name"], as_dict=True
	)
	if not employee:
		frappe.throw(_("Your account is not linked to an employee profile"))
	return user, employee


def _user_credential_ids(user: str) -> list[str]:
	return frappe.get_all("Passkey Credential", filters={"user": user}, pluck="credential_id")


def _parse_credential(credential) -> dict:
	if isinstance(credential, dict):
		data = credential
	else:
		try:
			data = json.loads(credential)
		except (TypeError, ValueError):
			frappe.throw(_("Invalid credential format"))
	if not isinstance(data, dict) or not data.get("id") or not isinstance(data.get("response"), dict):
		frappe.throw(_("Invalid credential format"))
	return data


def _get_credential_doc(credential_id: str):
	return frappe.db.get_value(
		"Passkey Credential",
		{"credential_id": credential_id},
		["name", "user", "employee", "credential_public_key", "sign_count"],
		as_dict=True,
	)


def _verify_or_throw(credential: dict, challenge_b64: str, cred_doc):
	if not cred_doc.credential_public_key:
		frappe.throw(_("This device needs to set up Face ID / fingerprint check-in again."))
	try:
		verified = verify_assertion(
			credential,
			expected_challenge_b64=challenge_b64,
			public_key_b64=cred_doc.credential_public_key,
			current_sign_count=cred_doc.sign_count,
		)
	except PasskeyVerificationError as error:
		frappe.throw(str(error))
	frappe.db.set_value(
		"Passkey Credential",
		cred_doc.name,
		{"sign_count": verified.new_sign_count, "last_used": now()},
		update_modified=False,
	)
	return verified


def _notify_new_device(user: str, device_name: str) -> None:
	frappe.get_doc(
		{
			"doctype": "PWA Notification",
			"from_user": "Administrator",
			"to_user": user,
			"notification_title": _("Face ID / fingerprint check-in was set up on a new device"),
			"message": _("{0} was added for check-in. If this wasn't you, please contact HR.").format(
				device_name
			),
			"target_route": "/settings",
		}
	).insert(ignore_permissions=True)


def _device_limit_message():
	return _("You already have {0} devices set up. Remove an old device in Settings first.").format(
		MAX_PASSKEYS_PER_EMPLOYEE
	)


@frappe.whitelist(methods=["POST"])
def register_options():
	user, employee = _require_employee_user()
	existing = _user_credential_ids(user)
	if len(existing) >= MAX_PASSKEYS_PER_EMPLOYEE:
		frappe.throw(_device_limit_message())
	return build_registration_options(
		user=user,
		display_name=employee.employee_name,
		exclude_credential_ids=existing,
		data={"user": user, "employee": employee.name},
	)


@frappe.whitelist(methods=["POST"])
def register_complete(credential: str, device_name: str | None = None):
	user, employee = _require_employee_user()
	data = _parse_credential(credential)
	challenge_b64 = extract_client_challenge(data)
	record = pop_challenge(PURPOSE_REGISTER, challenge_b64)
	if not record or record.get("user") != user:
		frappe.throw(_("Registration timeout, please try again"))
	try:
		verified = verify_registration(data, expected_challenge_b64=challenge_b64)
	except PasskeyVerificationError as error:
		frappe.throw(str(error))

	credential_id = bytes_to_base64url(verified.credential_id)
	if frappe.db.exists("Passkey Credential", {"credential_id": credential_id}):
		frappe.throw(_("This device is already set up."))
	existing_count = len(_user_credential_ids(user))
	if existing_count >= MAX_PASSKEYS_PER_EMPLOYEE:
		frappe.throw(_device_limit_message())

	doc = frappe.get_doc(
		{
			"doctype": "Passkey Credential",
			"user": user,
			"employee": employee.name,
			"credential_id": credential_id,
			"public_key": data["response"].get("attestationObject") or credential_id,
			"credential_public_key": bytes_to_base64url(verified.credential_public_key),
			"sign_count": verified.sign_count,
			"device_name": (device_name or _get_device_name_from_request())[:140],
		}
	)
	doc.insert(ignore_permissions=True)
	if existing_count:
		_notify_new_device(user, doc.device_name)
	return {"status": "ok", "message": _("Passkey registered successfully")}


def _require_enabled_location(location: str | None) -> str:
	if not location or not frappe.db.get_value("QR Checkin Location", location, "enabled"):
		frappe.throw(_("Check-in location is not available"))
	return location


@frappe.whitelist(allow_guest=True, methods=["POST", "GET"], xss_safe=True)
def auth_options(location: str | None = None):
	"""门口 NFC 页取认证选项（访客，可发现凭证）。"""
	location_name = _require_enabled_location(location)
	return build_authentication_options(
		allow_credential_ids=[], data={"location": location_name}, purpose=PURPOSE_NFC
	)


@frappe.whitelist(allow_guest=True, methods=["POST"], xss_safe=True)
def passkey_checkin(
	credential: str,
	location: str,
	latitude: float | None = None,
	longitude: float | None = None,
):
	"""门口 NFC 页打卡：核对通行密钥 → 在场判断 → 自动判断出勤/退勤。"""
	location_name = _require_enabled_location(location)
	data = _parse_credential(credential)
	cred_doc = _get_credential_doc(data["id"])
	if not cred_doc:
		frappe.throw(_("Passkey not found. Please register first."))

	challenge_b64 = extract_client_challenge(data)
	record = pop_challenge(PURPOSE_NFC, challenge_b64)
	if not record or record.get("location") != location_name:
		frappe.throw(_("Authentication timeout or invalid challenge"))
	_verify_or_throw(data, challenge_b64, cred_doc)

	client_ip = get_client_ip()
	presence = evaluate_presence(location_name, client_ip, latitude, longitude)
	if not presence.ok:
		frappe.throw(
			_(
				"We couldn't confirm you are at the office. Please scan the QR code at the entrance with the app."
			)
		)

	employee = cred_doc.employee
	log_type = resolve_auto_log_type(employee)
	validate_checkin_timing(employee, log_type)
	gps = presence.evidence == EVIDENCE_GPS
	checkin = create_checkin(
		employee=employee,
		log_type=log_type,
		location=location_name,
		method=CHECKIN_METHOD_NFC_PASSKEY,
		latitude=float(latitude) if gps else None,
		longitude=float(longitude) if gps else None,
		evidence=presence.evidence,
		client_ip=client_ip,
	)

	action = _("Check-in") if log_type == "IN" else _("Check-out")
	return {
		"status": "ok",
		"message": _("{0} successful").format(action),
		"log_type": log_type,
		"employee": employee,
		"employee_name": checkin.employee_name,
		"time": str(checkin.time),
		"location": location_name,
	}


def _passkey_checkin_location() -> str | None:
	location = frappe.db.get_single_value("HR Settings", "passkey_checkin_location")
	if location and frappe.db.get_value("QR Checkin Location", location, "enabled"):
		return location
	return None


def _passkey_checkin_enabled_for(employee: str) -> bool:
	if cint(frappe.db.get_single_value("HR Settings", "passkey_checkin_enabled_for_all")):
		return True
	return bool(
		frappe.db.exists(
			"Passkey Checkin Pilot Employee",
			{"parent": "HR Settings", "parentfield": "passkey_checkin_pilot_employees", "employee": employee},
		)
	)


@frappe.whitelist()
def get_checkin_context():
	user, employee = _require_employee_user()
	location = _passkey_checkin_location()
	enabled = bool(location) and _passkey_checkin_enabled_for(employee.name)
	return {
		"enabled": enabled,
		"has_passkey": bool(_user_credential_ids(user)),
		"on_office_network": is_office_network(get_client_ip()) if enabled else False,
		"location": {
			"name": location,
			"description": frappe.db.get_value("QR Checkin Location", location, "description") or location,
		}
		if enabled
		else None,
	}


@frappe.whitelist(methods=["POST"])
def begin_checkin(
	log_type: str,
	latitude: float | None = None,
	longitude: float | None = None,
	accuracy: float | None = None,
):
	user, employee = _require_employee_user()
	if log_type not in VALID_LOG_TYPES:
		frappe.throw(_("Invalid log type"))
	location = _passkey_checkin_location()
	if not location or not _passkey_checkin_enabled_for(employee.name):
		return {"status": "disabled"}

	client_ip = get_client_ip()
	presence = evaluate_presence(location, client_ip, latitude, longitude, accuracy)
	if not presence.ok:
		return {"status": presence.status, "reason": presence.reason}

	credential_ids = _user_credential_ids(user)
	if not credential_ids:
		return {"status": "no_passkey"}

	validate_checkin_timing(employee.name, log_type)
	gps = presence.evidence == EVIDENCE_GPS
	options = build_authentication_options(
		allow_credential_ids=credential_ids,
		data={
			"user": user,
			"employee": employee.name,
			"log_type": log_type,
			"location": location,
			"evidence": presence.evidence,
			"latitude": float(latitude) if gps else None,
			"longitude": float(longitude) if gps else None,
			"client_ip": client_ip,
		},
		purpose=PURPOSE_CHECKIN,
	)
	return {"status": "ok", "options": options, "evidence": presence.evidence}


@frappe.whitelist(methods=["POST"])
def complete_checkin(credential: str):
	user, employee = _require_employee_user()
	data = _parse_credential(credential)
	cred_doc = _get_credential_doc(data["id"])
	if not cred_doc or cred_doc.user != user:
		frappe.throw(_("This device isn't set up for your account. Please set it up again."))

	challenge_b64 = extract_client_challenge(data)
	record = pop_challenge(PURPOSE_CHECKIN, challenge_b64)
	if not record or record.get("user") != user:
		frappe.throw(_("Check-in timed out. Please try again."))
	_verify_or_throw(data, challenge_b64, cred_doc)

	validate_checkin_timing(employee.name, record["log_type"])
	checkin = create_checkin(
		employee=employee.name,
		log_type=record["log_type"],
		location=record["location"],
		method=CHECKIN_METHOD_PASSKEY,
		latitude=record.get("latitude"),
		longitude=record.get("longitude"),
		evidence=record.get("evidence"),
		client_ip=record.get("client_ip"),
	)
	return {
		"status": "ok",
		"log_type": checkin.log_type,
		"time": str(checkin.time),
		"employee": employee.name,
		"employee_name": checkin.employee_name,
		"location": record["location"],
		"evidence": record.get("evidence"),
	}


@frappe.whitelist()
def get_my_passkeys():
	"""
	获取当前用户的 Passkey 列表

	Returns:
	    [{"name": "xxx", "device_name": "iPhone 15", "created_at": "...", "last_used": "..."}]
	"""
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return []

	passkeys = frappe.get_all(
		"Passkey Credential",
		filters={"user": user},
		fields=["name", "device_name", "created_at", "last_used"],
		order_by="created_at desc",
	)

	return passkeys


@frappe.whitelist()
def delete_passkey(passkey_name: str):
	"""
	删除指定的 Passkey（只能删除自己的）

	Args:
	    passkey_name: Passkey Credential 文档名称

	Returns:
	    {"status": "ok", "message": "Passkey deleted"}
	"""
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		frappe.throw(_("Permission denied"))

	# 验证是否是自己的 Passkey
	passkey_user = frappe.db.get_value("Passkey Credential", passkey_name, "user")
	if passkey_user != user:
		frappe.throw(_("You can only delete your own Passkey"))

	frappe.delete_doc("Passkey Credential", passkey_name, ignore_permissions=True)
	frappe.db.commit()

	return {"status": "ok", "message": _("Passkey deleted")}


@frappe.whitelist()
def check_passkey_registered():
	"""
	检查当前用户是否已注册 Passkey

	Returns:
	    {"registered": True/False, "device_name": "..."}
	"""
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return {"registered": False}

	passkey = frappe.db.get_value(
		"Passkey Credential", {"user": user}, ["device_name", "created_at"], as_dict=True
	)

	if passkey:
		return {"registered": True, "device_name": passkey.device_name, "created_at": str(passkey.created_at)}

	return {"registered": False}


def _get_device_name_from_request() -> str:
	"""从请求 User-Agent 推断设备名称"""
	try:
		ua = frappe.local.request.headers.get("User-Agent", "")

		if "iPhone" in ua:
			return "iPhone"
		elif "iPad" in ua:
			return "iPad"
		elif "Android" in ua:
			if "Samsung" in ua:
				return "Samsung"
			elif "Pixel" in ua:
				return "Google Pixel"
			elif "Xiaomi" in ua or "Mi " in ua:
				return "Xiaomi"
			elif "HUAWEI" in ua:
				return "Huawei"
			return "Android Device"
		elif "Mac" in ua:
			return "Mac"
		elif "Windows" in ua:
			return "Windows PC"

		return "Unknown Device"
	except Exception:
		return "Unknown Device"
