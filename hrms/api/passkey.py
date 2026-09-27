# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

"""面容/指纹（通行密钥）打卡接口：设置、首页一键打卡、门口 NFC 页。"""

import base64
import json
import secrets
from datetime import timedelta

from webauthn.helpers import bytes_to_base64url

import frappe
from frappe import _
from frappe.utils import get_datetime, now, now_datetime

from hrms.api.checkin_cooldown import is_checkin_cooldown_exempt
from hrms.api.passkey_webauthn import (
	PURPOSE_REGISTER,
	PasskeyVerificationError,
	build_registration_options,
	extract_client_challenge,
	pop_challenge,
	verify_assertion,
	verify_registration,
)

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


# WebAuthn 配置（门口 NFC 页旧接口使用）
RP_ID = "erphr.toiroworld.com"
ORIGIN = "https://erphr.toiroworld.com"
CHALLENGE_TIMEOUT = 300


def _generate_challenge() -> bytes:
	"""生成随机 challenge"""
	return secrets.token_bytes(32)


def _b64_encode(data: bytes) -> str:
	"""URL-safe base64 编码"""
	return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
	"""URL-safe base64 解码"""
	padding = 4 - len(data) % 4
	if padding != 4:
		data += "=" * padding
	return base64.urlsafe_b64decode(data)


@frappe.whitelist(allow_guest=True, methods=["POST", "GET"], xss_safe=True)
def auth_options(location: str | None = None):
	"""
	步骤3: 获取 Passkey 验证选项（NFC 打卡时调用）

	Args:
	    location: 打卡地点（可选，用于日志）

	Returns:
	    WebAuthn authentication options (JSON)
	"""
	# 生成 challenge
	challenge = _generate_challenge()
	challenge_b64 = _b64_encode(challenge)

	# 保存 challenge 到缓存（用 challenge 本身作为 key，因为此时可能未登录）
	frappe.cache().set_value(
		f"passkey_auth_challenge:{challenge_b64}",
		json.dumps({"location": location, "created": str(now())}),
		expires_in_sec=CHALLENGE_TIMEOUT,
	)

	# 构建验证选项
	options = {
		"challenge": challenge_b64,
		"rpId": RP_ID,
		"timeout": CHALLENGE_TIMEOUT * 1000,
		"userVerification": "required",
		# 不指定 allowCredentials，允许任何已注册的 Passkey
	}

	return options


@frappe.whitelist(allow_guest=True, methods=["POST"], xss_safe=True)
def passkey_checkin(
	credential: str,
	location: str,
	latitude: float | None = None,
	longitude: float | None = None,
):
	"""
	步骤4: 使用 Passkey 验证并打卡

	Args:
	    credential: 前端返回的 credential JSON 字符串
	    location: 打卡地点

	Returns:
	    {
	        "status": "ok",
	        "log_type": "IN",
	        "employee_name": "张三",
	        "time": "2025-01-30 09:00:00",
	        "location": "office-2f-door"
	    }
	"""
	try:
		cred_data = json.loads(credential)
	except json.JSONDecodeError:
		frappe.throw(_("Invalid credential format"))

	# 获取 credential_id
	credential_id = cred_data.get("id")
	if not credential_id:
		frappe.throw(_("Missing credential ID"))

	# 查找对应的 Passkey Credential
	cred_doc = frappe.db.get_value(
		"Passkey Credential",
		{"credential_id": credential_id},
		["name", "user", "employee", "public_key", "sign_count"],
		as_dict=True,
	)

	if not cred_doc:
		frappe.throw(_("Passkey not found. Please register first."))

	# 解析 clientDataJSON
	client_data_json = _b64_decode(cred_data["response"]["clientDataJSON"])
	client_data = json.loads(client_data_json)

	# 获取 challenge
	challenge_b64 = client_data.get("challenge")

	# 验证 challenge 是否有效
	challenge_data = frappe.cache().get_value(f"passkey_auth_challenge:{challenge_b64}")
	if not challenge_data:
		frappe.throw(_("Authentication timeout or invalid challenge"))

	# 清除 challenge（一次性使用）
	frappe.cache().delete_value(f"passkey_auth_challenge:{challenge_b64}")

	# 验证 origin
	if client_data.get("origin") != ORIGIN:
		frappe.throw(_("Origin mismatch"))

	# 验证 type
	if client_data.get("type") != "webauthn.get":
		frappe.throw(_("Invalid operation type"))

	# 解析 authenticatorData 获取 sign_count
	authenticator_data = _b64_decode(cred_data["response"]["authenticatorData"])
	# sign_count 在 authenticatorData 的第 33-36 字节（大端序）
	new_sign_count = int.from_bytes(authenticator_data[33:37], "big")

	# 验证 sign_count（防重放攻击）
	if new_sign_count <= cred_doc.sign_count:
		# 警告但不阻止（某些设备 sign_count 可能不递增）
		frappe.log_error(
			message=f"Sign count not incremented for user {cred_doc.user}. Old: {cred_doc.sign_count}, New: {new_sign_count}",
			title="Passkey Sign Count Warning",
		)

	# 更新 sign_count 和 last_used
	frappe.db.set_value(
		"Passkey Credential", cred_doc.name, {"sign_count": new_sign_count, "last_used": now()}
	)

	# ===== 以下是打卡逻辑 =====
	employee = cred_doc.employee

	# 获取上次打卡记录，用于自动判断 IN/OUT
	last_checkin = frappe.db.get_value(
		"Employee Checkin", {"employee": employee}, ["log_type", "time"], order_by="time desc"
	)

	# 自动判断 IN/OUT
	if last_checkin:
		last_type, last_time = last_checkin
		# 如果今天有打卡记录
		if get_datetime(last_time).date() == now_datetime().date():
			log_type = "OUT" if last_type == "IN" else "IN"
		else:
			# 新的一天，从 IN 开始
			log_type = "IN"
	else:
		log_type = "IN"

	if not is_checkin_cooldown_exempt(employee):
		# 防重复打卡检查（5分钟内）
		recent_checkin = frappe.db.get_all(
			"Employee Checkin",
			filters={"employee": employee, "time": (">", now_datetime() - timedelta(minutes=5))},
			limit=1,
		)

		if recent_checkin:
			frappe.throw(_("You have already checked in within the last 5 minutes"))

	# 创建 Employee Checkin
	checkin_data = {
		"doctype": "Employee Checkin",
		"employee": employee,
		"time": now(),
		"log_type": log_type,
		"device_id": f"NFC-Passkey:{location}",
		"skip_auto_attendance": 0,
	}

	# 如果提供了地理位置，设置经纬度
	if latitude is not None and longitude is not None:
		checkin_data["latitude"] = latitude
		checkin_data["longitude"] = longitude

	checkin = frappe.get_doc(checkin_data)
	checkin.insert(ignore_permissions=True)
	frappe.db.commit()

	# 获取员工姓名
	employee_name = checkin.employee_name

	# 记录审计日志
	try:
		client_ip = frappe.local.request_ip or "Unknown"
		frappe.log_error(
			message=f"NFC-Passkey Checkin: Employee {employee} ({employee_name}) {log_type} at {location}. IP: {client_ip}",
			title=f"NFC-Passkey Checkin - {log_type}",
		)
	except Exception:
		pass

	action = _("Check-in") if log_type == "IN" else _("Check-out")
	return {
		"status": "ok",
		"message": _("{0} successful").format(action),
		"log_type": log_type,
		"employee": employee,
		"employee_name": employee_name,
		"time": str(checkin.time),
		"location": location,
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
