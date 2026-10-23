"""签到牌的蓝牙码：手机靠近签到牌时收到的滚动码，密钥只留在服务器和签到牌上。"""

import hashlib
import hmac
import re
import time

import frappe
from frappe.utils import cint
from frappe.utils.password import get_decrypted_password

from hrms.api.passkey import _passkey_checkin_enabled_for, _passkey_checkin_location

SLOT_SECONDS = 10
PAST_SLOTS = 3
FUTURE_SLOTS = 1

_KEY_PATTERN = re.compile(r"[0-9a-fA-F]{64}")
_CODE_PATTERN = re.compile(r"[0-9a-fA-F]{8}")


def _now() -> float:
	return time.time()


def beacon_slot(ts: float | None = None) -> int:
	"""Unix 秒换算成 10 秒一格的时间段。"""
	return int(_now() if ts is None else ts) // SLOT_SECONDS


def beacon_code(key_hex: str, location: str, slot: int) -> str:
	"""HMAC-SHA256 的前 4 字节，8 位小写十六进制。"""
	message = f"uohr-ble:v1:{location}:{slot}".encode()
	return hmac.new(bytes.fromhex(key_hex), message, hashlib.sha256).digest()[:4].hex()


def _location_ble_key(location: str) -> str | None:
	return get_decrypted_password("QR Checkin Location", location, "ble_key", raise_exception=False)


def _valid_slot(slot) -> bool:
	return isinstance(slot, int) and not isinstance(slot, bool) and slot >= 0


def beacon_slot_offset(slot, now: float | None = None) -> int | None:
	"""收到的时间段比当前早（负）或晚（正）几格；不合法返回 None，给失败记录用。"""
	if not _valid_slot(slot):
		return None
	return slot - beacon_slot(now)


def verify_beacon(location: str, slot, code, now: float | None = None) -> bool:
	"""核对手机上报的蓝牙码；任何一处不对都只返回 False，不抛异常。"""
	if not _valid_slot(slot) or not isinstance(code, str) or not _CODE_PATTERN.fullmatch(code):
		return False

	offset = beacon_slot_offset(slot, now)
	if offset < -PAST_SLOTS or offset > FUTURE_SLOTS:
		return False

	key = _location_ble_key(location)
	if not isinstance(key, str) or not _KEY_PATTERN.fullmatch(key):
		return False

	expected = beacon_code(key, location, slot)
	return hmac.compare_digest(expected.encode(), code.lower().encode())


def ble_checkin_enabled_for(employee: str) -> bool:
	"""蓝牙打卡对这个人是否生效：总开关开着、手机钥匙打卡对他开着、打卡点有合法的蓝牙密钥。"""
	if not cint(frappe.db.get_single_value("HR Settings", "ble_checkin_enabled")):
		return False
	location = _passkey_checkin_location()
	if not location or not _passkey_checkin_enabled_for(employee):
		return False
	# 只用来判断「有没有合法密钥」，不往外传
	key = _location_ble_key(location)
	return isinstance(key, str) and bool(_KEY_PATTERN.fullmatch(key))
