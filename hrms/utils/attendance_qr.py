"""Shared QR payload for web and hardware displays; signing secrets stay on the server."""

import hashlib
import hmac
import time

TIME_SLOT_SECONDS = 30


def get_refresh_interval(location):
	return int(location.qr_refresh_interval or TIME_SLOT_SECONDS)


def _get_time_slot(ts=None, interval=TIME_SLOT_SECONDS):
	return int(time.time() if ts is None else ts) // interval


def _sign(location_name: str, time_slot: int, secret: str) -> str:
	message = f"{location_name}|{time_slot}"
	return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()[:8]


def build_qr_payload(location):
	server_time = int(time.time())
	interval = get_refresh_interval(location)
	slot = _get_time_slot(server_time, interval)
	signature = _sign(location.name, slot, location.get_password("secret"))
	return {
		"token": f"{location.name}|{slot}|{signature}",
		"expires_in": interval,
		"location": location.name,
		"description": location.description,
		"server_time": server_time,
		"refresh_at": (slot + 1) * interval,
		"expires_at": (slot + 2) * interval,
	}
