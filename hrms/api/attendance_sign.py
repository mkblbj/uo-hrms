"""Read-only HTTPS interface for the attendance sign. Never creates check-ins."""

import hmac
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_datetime, get_system_timezone

from hrms.utils.attendance_sign_audio import find_clip, read_asset


def _require_sign_key(location: str):
	if not location or not frappe.db.exists("QR Checkin Location", location):
		raise frappe.PermissionError("Invalid attendance sign configuration")
	doc = frappe.get_doc("QR Checkin Location", location)
	expected = doc.get_password("display_key", raise_exception=False)
	supplied = frappe.get_request_header("X-Attendance-Sign-Key")
	if (
		not doc.enabled
		or not expected
		or not supplied
		or not hmac.compare_digest(str(expected).encode(), str(supplied).encode())
	):
		raise frappe.PermissionError("Invalid attendance sign configuration")
	return doc


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_qr(location: str) -> dict:
	"""Return the server-signed QR payload for a key-authenticated display."""
	from hrms.utils.attendance_qr import build_qr_payload

	doc = _require_sign_key(location)
	frappe.local.response_headers["Cache-Control"] = "no-store"
	return {"version": 1, "locale": "ja-JP", **build_qr_payload(doc)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_events(location: str) -> dict:
	_require_sign_key(location)
	frappe.local.response_headers["Cache-Control"] = "no-store"
	server_time = time.time()
	timezone = ZoneInfo(get_system_timezone())
	now = datetime.fromtimestamp(server_time, timezone).replace(tzinfo=None)
	rows = frappe.get_all(
		"Employee Checkin",
		filters={
			"device_id": location,
			"creation": ["between", [now - timedelta(seconds=30), now]],
			"checkin_method": ["in", ["QR", "Passkey"]],
			"log_type": ["in", ["IN", "OUT"]],
		},
		fields=["name", "employee", "employee_name", "log_type", "time", "creation"],
		order_by="creation desc, name desc",
		limit=20,
	)
	events = []
	for row in reversed(rows):
		asset_id = find_clip(row.employee, row.employee_name, row.log_type)
		events.append(
			{
				"id": row.name,
				"employee_id": row.employee,
				"employee_name": row.employee_name,
				"log_type": row.log_type,
				"time_label": get_datetime(row.time).strftime("%H:%M"),
				"created_at": get_datetime(row.creation).replace(tzinfo=timezone).timestamp(),
				"action_label": "出勤完了" if row.log_type == "IN" else "退勤完了",
				"greeting": "おはようございます。" if row.log_type == "IN" else "お疲れさまでした。",
				"audio_url": (
					"/api/method/hrms.api.attendance_sign.get_audio?"
					+ urlencode({"location": location, "asset_id": asset_id})
				)
				if asset_id
				else None,
			}
		)
	return {"version": 1, "server_time": server_time, "locale": "ja-JP", "events": events}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_audio(location: str, asset_id: str):
	_require_sign_key(location)
	data = read_asset(asset_id)
	frappe.local.response_headers["Cache-Control"] = "no-store"
	frappe.response.update(
		type="download",
		filename=f"{asset_id}.wav",
		filecontent=data,
		content_type="audio/wav",
		display_content_as="inline",
	)
