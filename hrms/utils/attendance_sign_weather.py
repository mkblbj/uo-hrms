"""Compact board weather from the server's own weather source (only the sign shows weather now), with site-scoped Redis caching."""

import math
import re
import time

import frappe
from frappe.utils import nowdate

FRESH_SECONDS = 600
RETRY_SECONDS = 60
HISTORY_SECONDS = 3600

# WeatherAPI's published icon IDs; unknown IDs keep their text and use a generic icon.
# https://www.weatherapi.com/docs/weather_conditions.json
ICON_GROUPS = {
	"clear": {113},
	"partly_cloudy": {116},
	"cloudy": {119, 122},
	"fog": {143, 248, 260},
	"rain": {176, 185, 263, 266, 281, 284, 293, 296, 299, 302, 305, 308, 311, 314, 353, 356, 359},
	"snow": {179, 227, 230, 323, 326, 329, 332, 335, 338, 368, 371},
	"sleet": {182, 317, 320, 350, 362, 365, 374, 377},
	"thunder": {200, 386, 389, 392, 395},
}


def _source():
	from hrms.api import get_weather_data

	previous = getattr(frappe.local, "lang", None)
	try:
		frappe.local.lang = "ja"
		return get_weather_data()
	except Exception as exc:
		# Do not include upstream URLs, credentials or exception text in the device response/log.
		frappe.log_error(
			title="Attendance Sign Weather", message=f"Weather source unavailable ({type(exc).__name__})"
		)
		return None
	finally:
		frappe.local.lang = previous


def _number(value):
	return (
		value
		if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
		else None
	)


def _normalize(data):
	if not isinstance(data, dict) or _number(data.get("temp_c")) is None:
		return None
	condition = data.get("condition")
	if (
		not isinstance(condition, dict)
		or not isinstance(condition.get("text"), str)
		or not condition["text"].strip()
	):
		return None
	match = re.search(r"/(day|night)/(\d+)\.png(?:\?.*)?$", str(condition.get("icon", "")))
	icon = "unknown"
	is_day = None
	if match:
		is_day = match[1] == "day"
		icon_id = int(match[2])
		icon = next((name for name, ids in ICON_GROUPS.items() if icon_id in ids), "unknown")
	return {
		"temp_c": data["temp_c"],
		"maxtemp_c": _number(data.get("maxtemp_c")),
		"mintemp_c": _number(data.get("mintemp_c")),
		"condition_text": condition["text"].strip(),
		"icon_key": icon,
		"is_day": is_day,
	}


def _cache_key(day):
	return f"attendance-sign:weather:v1:ja:{day}"


def get_snapshot():
	day = nowdate()
	key = _cache_key(day)
	now = int(time.time())
	record = frappe.cache.get_value(key, use_local_cache=False)
	if not record or record["retry_at"] <= now:
		current = _normalize(_source())
		now = int(time.time())
		if current is not None:
			record = {"status": "ok", "weather": current, "fetched_at": now, "retry_at": now + FRESH_SECONDS}
			frappe.cache.set_value(key + ":last-good", record, expires_in_sec=HISTORY_SECONDS)
			ttl = FRESH_SECONDS
		else:
			old = frappe.cache.get_value(key + ":last-good", use_local_cache=False)
			usable = old is not None and 0 <= now - old["fetched_at"] <= HISTORY_SECONDS
			record = {
				"status": "stale" if usable else "unavailable",
				"weather": old["weather"] if usable else None,
				"fetched_at": old["fetched_at"] if usable else None,
				"retry_at": now + RETRY_SECONDS,
			}
			ttl = RETRY_SECONDS
		frappe.cache.set_value(key, record, expires_in_sec=ttl)
	if record["status"] == "stale" and now - record["fetched_at"] > HISTORY_SECONDS:
		record = {**record, "status": "unavailable", "weather": None, "fetched_at": None}
	return {
		"status": record["status"],
		"weather": record["weather"],
		"fetched_at": record["fetched_at"],
		"date": day,
		"refresh_after": max(
			1, min(FRESH_SECONDS if record["status"] == "ok" else RETRY_SECONDS, record["retry_at"] - now)
		),
	}
