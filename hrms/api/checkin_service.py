"""扫码、NFC、一键打卡共用的打卡规则与建记录。"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_datetime, now, now_datetime

from hrms.api.checkin_cooldown import is_checkin_cooldown_exempt

CHECKIN_METHOD_QR = "QR"
CHECKIN_METHOD_PASSKEY = "Passkey"
CHECKIN_METHOD_NFC_PASSKEY = "NFC Passkey"
CHECKIN_METHOD_CORRECTION = "Attendance Correction"

AUDIT_TITLES = {
	CHECKIN_METHOD_QR: "QR Checkin Audit",
	CHECKIN_METHOD_PASSKEY: "Passkey Checkin Audit",
	CHECKIN_METHOD_NFC_PASSKEY: "NFC-Passkey Checkin",
}


def validate_checkin_timing(employee: str, log_type: str) -> None:
	if is_checkin_cooldown_exempt(employee):
		return

	last_checkin = frappe.db.get_value(
		"Employee Checkin", {"employee": employee}, ["log_type", "time"], order_by="time desc"
	)
	if last_checkin:
		last_type, last_time = last_checkin
		minutes_since = (now_datetime() - get_datetime(last_time)).total_seconds() / 60
		if last_type == "IN" and log_type == "OUT" and minutes_since < 15:
			frappe.throw(
				_(
					"You just checked in {0} minutes ago. Please wait at least 15 minutes before checking out."
				).format(int(minutes_since))
			)
		if last_type == "OUT" and log_type == "IN" and minutes_since < 5:
			frappe.throw(
				_(
					"You just checked out {0} minutes ago. Please wait at least 5 minutes before checking in."
				).format(int(minutes_since))
			)

	recent_checkin = frappe.db.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"log_type": log_type,
			"time": (">", now_datetime() - timedelta(minutes=5)),
		},
		limit=1,
	)
	if recent_checkin:
		action = _("checked in") if log_type == "IN" else _("checked out")
		frappe.throw(
			_("You have already {0} within the last 5 minutes, please do not check in repeatedly").format(
				action
			)
		)


def resolve_auto_log_type(employee: str) -> str:
	last_checkin = frappe.db.get_value(
		"Employee Checkin", {"employee": employee}, ["log_type", "time"], order_by="time desc"
	)
	if last_checkin and get_datetime(last_checkin[1]).date() == now_datetime().date():
		return "OUT" if last_checkin[0] == "IN" else "IN"
	return "IN"


def create_checkin(
	*,
	employee: str,
	log_type: str,
	location: str,
	method: str,
	latitude: float | None = None,
	longitude: float | None = None,
	evidence: str | None = None,
	client_ip: str | None = None,
):
	data = {
		"doctype": "Employee Checkin",
		"employee": employee,
		"time": now(),
		"log_type": log_type,
		"device_id": location,
		"checkin_method": method,
		"skip_auto_attendance": 0,
	}
	if latitude is not None and longitude is not None:
		data["latitude"] = latitude
		data["longitude"] = longitude

	checkin = frappe.get_doc(data)
	checkin.flags.trusted_checkin_source = True
	checkin.insert(ignore_permissions=True)

	_write_audit(checkin, method=method, location=location, evidence=evidence, client_ip=client_ip)
	publish_checkin_notification(checkin, location)
	return checkin


def _write_audit(checkin, *, method, location, evidence, client_ip):
	title = AUDIT_TITLES.get(method, "Checkin Audit")
	geo = ""
	if checkin.latitude and checkin.longitude:
		geo = f" (Lat: {checkin.latitude:.5f}, Lng: {checkin.longitude:.5f})"
	message = (
		f"{title}: Employee {checkin.employee} ({checkin.employee_name}) {checkin.log_type} "
		f"at {location} on {checkin.time}. IP: {client_ip or 'Unknown'}{geo} Evidence: {evidence or '-'}"
	)
	try:
		frappe.logger().info(message)
		frappe.log_error(title=f"{title} - {checkin.log_type}", message=message)
	except Exception:
		frappe.log_error(title="Checkin Audit Log Error")


def publish_checkin_notification(checkin, location: str) -> None:
	try:
		action_ja = "出勤" if checkin.log_type == "IN" else "退勤"
		frappe.publish_realtime(
			event="qr_checkin_notification",
			message={
				"employee_name": checkin.employee_name,
				"employee_image": frappe.db.get_value("Employee", checkin.employee, "image"),
				"log_type": checkin.log_type,
				"action_ja": action_ja,
				"location": location,
				"time": str(checkin.time),
				"message_ja": f"{checkin.employee_name}さんが{action_ja}しました。お疲れ様です！",
			},
			room=f"qr_location_{location}",
			after_commit=True,
		)
	except Exception:
		frappe.log_error(title="QR Checkin Notification Error")
