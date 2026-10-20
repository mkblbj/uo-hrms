# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""App 的面容打卡（手机钥匙）：登记、首页一键打卡。

App 在手机的 Secure Enclave 里生成一把只有本人面容能用的 P-256 钥匙，打卡时用它给服务器的
一次性验证码签名，所以点一下只有面容动画、没有通行密钥的系统确认框。在场判断、冷却、
打卡记录的写法和网页的通行密钥打卡（hrms.api.passkey）完全一样，只是「证明是本人」的方式换了。

和 App 的约定：签名是 ECDSA P-256 + SHA-256（DER），签的是 UTF-8 字符串
"uohr-device-key:<register|checkin>:<challenge>"；公钥是 X9.63 未压缩点（65 字节）；
key_id = base64url(sha256(公钥字节))；二进制一律 base64url 不带填充。
"""

import hashlib
import secrets

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

import frappe
from frappe import _
from frappe.utils import escape_html, get_datetime, now, now_datetime
from frappe.utils.password import check_password

from hrms.api.checkin_presence import evaluate_presence, normalize_coordinates
from hrms.api.checkin_service import CHECKIN_METHOD_DEVICE_KEY, create_checkin, validate_checkin_timing
from hrms.api.passkey import (
	VALID_LOG_TYPES,
	_get_device_name_from_request,
	_passkey_checkin_enabled_for,
	_passkey_checkin_location,
	_require_employee_user,
)
from hrms.api.passkey_webauthn import b64url_decode, b64url_encode, pop_challenge, store_challenge
from hrms.utils.client_network import get_client_ip, is_office_network

DOCTYPE = "Device Checkin Key"
MAX_DEVICE_KEYS_PER_EMPLOYEE = 3

PURPOSE_REGISTER = "device_register"
PURPOSE_CHECKIN = "device_checkin"
REGISTRATION_TIMEOUT_SECONDS = 300
CHECKIN_TIMEOUT_SECONDS = 120

# 拿着别人的手机反复试 ERP 密码：同一账号 10 分钟内错 5 次，暂停登记 10 分钟
PASSWORD_MAX_FAILURES = 5
PASSWORD_FAILURE_WINDOW_SECONDS = 600
PASSWORD_LOCK_SECONDS = 600

INPUT_ERRORS = (ValueError, TypeError)


class DeviceKeyError(frappe.ValidationError):
	pass


def _signed_message(purpose: str, challenge: str) -> bytes:
	return f"uohr-device-key:{purpose}:{challenge}".encode()


def _load_public_key(public_key_b64: str) -> tuple[bytes, ec.EllipticCurvePublicKey]:
	"""base64url 的 X9.63 未压缩点 → (原始字节, 公钥)；格式不对或不在曲线上时抛 ValueError。"""
	raw = b64url_decode(public_key_b64)
	if len(raw) != 65 or raw[0] != 0x04:
		raise ValueError("expected an uncompressed P-256 point")
	return raw, ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), raw)


def _signature_valid(
	public_key: ec.EllipticCurvePublicKey, purpose: str, challenge: str, signature: str
) -> bool:
	try:
		public_key.verify(
			b64url_decode(signature), _signed_message(purpose, challenge), ec.ECDSA(hashes.SHA256())
		)
	except (InvalidSignature, *INPUT_ERRORS):
		return False
	return True


def _key_id(raw_public_key: bytes) -> str:
	return b64url_encode(hashlib.sha256(raw_public_key).digest())


def _own_key(user: str, key_id: str | None):
	if not key_id:
		return None
	return frappe.db.get_value(
		DOCTYPE, {"key_id": key_id, "user": user}, ["name", "public_key"], as_dict=True
	)


def _key_count(user: str, excluding: str | None = None) -> int:
	filters = {"user": user}
	if excluding:
		filters["key_id"] = ("!=", excluding)
	return frappe.db.count(DOCTYPE, filters)


# ---- 密码限次 ----


# scope 区分用途：手机钥匙登记和 App 里改密码各自计数，规则相同
def _failure_key(user: str, scope: str = "device_key") -> str:
	return f"{scope}_password_failures:{user}"


def _lock_key(user: str, scope: str = "device_key") -> str:
	return f"{scope}_password_lock:{user}"


def _password_locked(user: str, scope: str = "device_key") -> bool:
	return bool(frappe.cache.exists(_lock_key(user, scope)))


def _claim_password_attempt(user: str, scope: str = "device_key") -> int:
	"""核对密码之前先占一次尝试，返回这是窗口内的第几次。先占后核对，同时发很多请求也只能核对 5 次。
	窗口从第一次尝试算起 10 分钟；输对一次就清零，所以实际数的是连续输错的次数。"""
	key = frappe.cache.make_key(_failure_key(user, scope))
	attempt = frappe.cache.incr(key)
	if attempt == 1:
		frappe.cache.expire(key, PASSWORD_FAILURE_WINDOW_SECONDS)
	return attempt


def _lock_password(user: str, scope: str = "device_key") -> None:
	frappe.cache.set_value(_lock_key(user, scope), 1, expires_in_sec=PASSWORD_LOCK_SECONDS)
	frappe.cache.delete_value(_failure_key(user, scope))


def _password_ok(user: str, password: str) -> bool:
	try:
		# 不清 Frappe 登录失败的计数：这里输错输对都不影响登录页的锁定
		check_password(user, password, delete_tracker_cache=False)
	except frappe.AuthenticationError:
		return False
	return True


# ---- 接口 ----


def _require_login() -> str:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please login first"), frappe.PermissionError)
	return user


def _timestamp(value) -> str | None:
	return get_datetime(value).strftime("%Y-%m-%d %H:%M:%S") if value else None


@frappe.whitelist(methods=["GET"])
def list_my_keys() -> dict:
	"""本人登记过的手机钥匙（不含网页的通行密钥），新登记的在前。只要登录，不要求员工档案。"""
	user = _require_login()
	rows = frappe.get_all(
		DOCTYPE,
		filters={"user": user},
		fields=["key_id", "device_name", "creation", "last_used"],
		order_by="creation desc",
	)
	return {
		"keys": [
			{
				"key_id": row.key_id,
				"device_name": row.device_name,
				"registered_at": _timestamp(row.creation),
				"last_used": _timestamp(row.last_used),
			}
			for row in rows
		],
		"max": MAX_DEVICE_KEYS_PER_EMPLOYEE,
	}


@frappe.whitelist(methods=["POST"])
def delete_my_key(key_id: str | None = None) -> dict:
	"""删掉本人的一把手机钥匙。那台手机下次打卡会得到 no_device_key，要重新设置。不发通知。"""
	user = _require_login()
	if not key_id:
		frappe.throw(_("Invalid key ID"))
	key = _own_key(user, key_id)
	if key:
		frappe.delete_doc(DOCTYPE, key.name, ignore_permissions=True)
	return {"status": "ok" if key else "not_found", "key_count": _key_count(user)}


@frappe.whitelist(methods=["GET"])
def get_checkin_context() -> dict:
	user, employee = _require_employee_user()
	location = _passkey_checkin_location()
	enabled = bool(location) and _passkey_checkin_enabled_for(employee.name)
	return {
		"enabled": enabled,
		"on_office_network": is_office_network(get_client_ip()) if enabled else False,
		"location": {
			"name": location,
			"description": frappe.db.get_value("QR Checkin Location", location, "description") or location,
		}
		if enabled
		else None,
		"key_count": _key_count(user),
	}


@frappe.whitelist(methods=["POST"])
def register_options(password: str, replaces_key_id: str | None = None) -> dict:
	user, employee = _require_employee_user()
	if _password_locked(user):
		return {"status": "too_many_attempts"}
	attempt = _claim_password_attempt(user)
	if attempt > PASSWORD_MAX_FAILURES:
		return {"status": "too_many_attempts"}
	if not _password_ok(user, password):
		if attempt < PASSWORD_MAX_FAILURES:
			return {"status": "wrong_password"}
		_lock_password(user)
		return {"status": "too_many_attempts"}
	frappe.cache.delete_value(_failure_key(user))

	replaces = replaces_key_id if _own_key(user, replaces_key_id) else None
	if _key_count(user, excluding=replaces) >= MAX_DEVICE_KEYS_PER_EMPLOYEE:
		return {"status": "device_limit"}

	challenge = store_challenge(
		PURPOSE_REGISTER,
		secrets.token_bytes(32),
		{"user": user, "employee": employee.name, "password_verified": True, "replaces_key_id": replaces},
		REGISTRATION_TIMEOUT_SECONDS,
	)
	return {"status": "ok", "challenge": challenge, "timeout": REGISTRATION_TIMEOUT_SECONDS * 1000}


def _setup_failed():
	frappe.throw(_("Face ID check-in could not be set up. Please try again."), DeviceKeyError)


@frappe.whitelist(methods=["POST"])
def register_complete(
	challenge: str, public_key: str, signature: str, device_name: str | None = None
) -> dict:
	user, employee = _require_employee_user()
	record = pop_challenge(PURPOSE_REGISTER, challenge)
	if not record or record.get("user") != user or record.get("password_verified") is not True:
		frappe.throw(_("Setup timed out. Please try again."), DeviceKeyError)
	try:
		raw, key = _load_public_key(public_key)
	except INPUT_ERRORS:
		_setup_failed()
	if not _signature_valid(key, "register", challenge, signature):
		_setup_failed()

	key_id = _key_id(raw)
	if frappe.db.exists(DOCTYPE, {"key_id": key_id}):
		_setup_failed()

	# 钥匙作废后重设：先删掉本人的旧钥匙，不占设备名额
	replaced = _own_key(user, record.get("replaces_key_id"))
	if replaced:
		frappe.delete_doc(DOCTYPE, replaced.name, ignore_permissions=True)
	# 同一账号同时登记几台时在这里排队，用加锁读数到已提交的最新钥匙数，不会超过 3 把
	frappe.db.get_value("User", user, "name", for_update=True)
	keys = frappe.db.get_values(DOCTYPE, {"user": user}, "name", for_update=True)
	if len(keys) >= MAX_DEVICE_KEYS_PER_EMPLOYEE:
		frappe.throw(
			_("You already have {0} devices set up.").format(MAX_DEVICE_KEYS_PER_EMPLOYEE), DeviceKeyError
		)

	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"user": user,
			"employee": employee.name,
			"key_id": key_id,
			"public_key": b64url_encode(raw),
			"device_name": (device_name or _get_device_name_from_request())[:140],
		}
	).insert(ignore_permissions=True)
	_notify_key_registered(user, doc.device_name)
	return {"status": "ok", "key_id": key_id}


def _notify_key_registered(user: str, device_name: str) -> None:
	"""每次登记（包括第一把和替换）都告诉本人，防止别人拿着手机偷偷设置。"""
	frappe.get_doc(
		{
			"doctype": "PWA Notification",
			"from_user": "Administrator",
			"to_user": user,
			"notification_type": "Other",
			"notification_title": "顔認証打刻の端末が登録されました",
			"message": f"{now_datetime().strftime('%Y-%m-%d %H:%M')} に「{escape_html(device_name)}」が登録されました。"
			"心当たりがない場合は HR に連絡してください。",
		}
	).insert(ignore_permissions=True)


@frappe.whitelist(methods=["POST"])
def begin_checkin(
	log_type: str,
	key_id: str | None = None,
	latitude: float | None = None,
	longitude: float | None = None,
	accuracy: float | None = None,
) -> dict:
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

	if not _own_key(user, key_id):
		return {"status": "no_device_key"}

	validate_checkin_timing(employee.name, log_type)
	coordinates = normalize_coordinates(latitude, longitude) or (None, None)
	challenge = store_challenge(
		PURPOSE_CHECKIN,
		secrets.token_bytes(32),
		{
			"user": user,
			"employee": employee.name,
			"log_type": log_type,
			"location": location,
			"evidence": presence.evidence,
			"latitude": coordinates[0],
			"longitude": coordinates[1],
			"client_ip": client_ip,
			"key_id": key_id,
		},
		CHECKIN_TIMEOUT_SECONDS,
	)
	return {"status": "ok", "challenge": challenge, "evidence": presence.evidence}


@frappe.whitelist(methods=["POST"])
def complete_checkin(challenge: str, key_id: str, signature: str) -> dict:
	user, employee = _require_employee_user()
	record = pop_challenge(PURPOSE_CHECKIN, challenge)
	if not record or record.get("user") != user or record.get("key_id") != key_id:
		frappe.throw(_("Check-in timed out. Please try again."), DeviceKeyError)
	key_doc = _own_key(user, key_id)
	if not key_doc:
		frappe.throw(_("This device isn't set up for your account. Please set it up again."), DeviceKeyError)
	try:
		_raw, public_key = _load_public_key(key_doc.public_key)
	except INPUT_ERRORS:
		public_key = None
	if not public_key or not _signature_valid(public_key, "checkin", challenge, signature):
		frappe.throw(_("Face ID could not be verified. Please try again."), DeviceKeyError)

	validate_checkin_timing(employee.name, record["log_type"])
	checkin = create_checkin(
		employee=employee.name,
		log_type=record["log_type"],
		location=record["location"],
		method=CHECKIN_METHOD_DEVICE_KEY,
		latitude=record.get("latitude"),
		longitude=record.get("longitude"),
		evidence=record.get("evidence"),
		client_ip=record.get("client_ip"),
	)
	frappe.db.set_value(DOCTYPE, key_doc.name, "last_used", now(), update_modified=False)
	return {
		"status": "ok",
		"log_type": checkin.log_type,
		"time": str(checkin.time),
		"employee": employee.name,
		"employee_name": checkin.employee_name,
		"location": record["location"],
		"evidence": record.get("evidence"),
	}
