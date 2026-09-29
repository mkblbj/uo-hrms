"""打卡前的定位：连着公司网络就不用定位；手机拿不到定位时记下原因（不记位置）。"""

import re

import frappe
from frappe import _
from frappe.utils import cint

from hrms.utils.client_network import get_client_ip, is_office_network

FAILURE_TITLE = "Checkin Location Failure"
FAILURE_REASONS = frozenset({"denied", "unavailable", "timeout", "unsupported"})
FAILURE_FLOWS = frozenset({"qr", "passkey"})
REPORTS_PER_HOUR = 20
MAX_REPORTED_WAIT_MS = 10 * 60 * 1000


def is_location_required(on_office_network: bool) -> bool:
	"""开着地理位置追踪、人又不在公司网络时，打卡才需要手机定位。"""
	if on_office_network:
		return False
	return bool(cint(frappe.db.get_single_value("HR Settings", "allow_geolocation_tracking")))


@frappe.whitelist()
def get_location_requirement():
	on_office_network = is_office_network(get_client_ip())
	return {
		"location_required": is_location_required(on_office_network),
		"on_office_network": on_office_network,
	}


@frappe.whitelist(methods=["POST"])
def report_location_failure(flow: str, reason: str, elapsed_ms: int | None = None):
	"""手机拿不到定位时调用：只记失败类型、等了多久和机型，方便统计哪类问题最多。"""
	if flow not in FAILURE_FLOWS or reason not in FAILURE_REASONS:
		frappe.throw(_("Invalid location report"))
	user = frappe.session.user
	if not frappe.db.exists("Employee", {"user_id": user}) or not _count_report(user):
		return {"status": "skipped"}
	waited = min(max(cint(elapsed_ms), 0), MAX_REPORTED_WAIT_MS)
	frappe.log_error(
		title=f"{FAILURE_TITLE} - {reason}",
		message=f"Flow: {flow}\nWaited: {waited}ms\nDevice: {_device_summary()}",
	)
	return {"status": "ok"}


def _count_report(user: str) -> bool:
	"""每人每小时最多记 REPORTS_PER_HOUR 条，防止反复重试把日志刷满。"""
	key = frappe.cache.make_key(f"hrms:checkin-location-failures:{user}")
	count = frappe.cache.incr(key)
	# 首次计数设一小时过期；上次设过期失败留下的无期限计数也补上，免得一直被拦
	if count == 1 or frappe.cache.ttl(key) < 0:
		frappe.cache.expire(key, 3600)
	return count <= REPORTS_PER_HOUR


def _device_summary() -> str:
	try:
		agent = frappe.local.request.headers.get("User-Agent", "")
	except (AttributeError, RuntimeError):
		agent = ""
	ios = re.search(r"\((iPhone|iPad)\b.*?OS (\d+)_(\d+)", agent)
	if ios:
		return f"{ios.group(1)} iOS {ios.group(2)}.{ios.group(3)}"
	android = re.search(r"Android (\d+(?:\.\d+)?)", agent)
	if android:
		return f"Android {android.group(1)}"
	return "Other"
