"""判断人在不在公司：公司网络，或手机定位在打卡点半径内。"""

import math
from dataclasses import dataclass

import frappe

from hrms.hr.utils import get_distance_between_coordinates
from hrms.utils.client_network import is_office_network

EVIDENCE_OFFICE_NETWORK = "office_network"
EVIDENCE_GPS = "gps"
STATUS_OK = "ok"
STATUS_NEED_LOCATION = "need_location"
STATUS_UNCONFIRMED = "presence_unconfirmed"


@dataclass(frozen=True)
class PresenceResult:
	status: str
	evidence: str | None = None
	reason: str | None = None
	distance: float | None = None

	@property
	def ok(self) -> bool:
		return self.status == STATUS_OK


def _to_float(value) -> float | None:
	try:
		number = float(value)
	except (TypeError, ValueError):
		return None
	return number if math.isfinite(number) else None


def _valid_coordinates(latitude, longitude) -> tuple[float, float] | None:
	lat, lng = _to_float(latitude), _to_float(longitude)
	if lat is None or lng is None:
		return None
	if not (-90 <= lat <= 90 and -180 <= lng <= 180) or (lat == 0 and lng == 0):
		return None
	return lat, lng


def get_location_geofence(location_name: str):
	shift_location = frappe.db.get_value("QR Checkin Location", location_name, "shift_location")
	if not shift_location:
		return None
	geofence = frappe.db.get_value(
		"Shift Location", shift_location, ["latitude", "longitude", "checkin_radius"], as_dict=True
	)
	if not geofence or not _valid_coordinates(geofence.latitude, geofence.longitude):
		return None
	if not geofence.checkin_radius or geofence.checkin_radius <= 0:
		return None
	return geofence


def evaluate_presence(
	location_name, client_ip, latitude=None, longitude=None, accuracy=None
) -> PresenceResult:
	if is_office_network(client_ip):
		return PresenceResult(STATUS_OK, EVIDENCE_OFFICE_NETWORK)

	coordinates = _valid_coordinates(latitude, longitude)
	if not coordinates:
		return PresenceResult(STATUS_NEED_LOCATION)

	geofence = get_location_geofence(location_name)
	if not geofence:
		return PresenceResult(STATUS_UNCONFIRMED, reason="no_geofence")

	radius = float(geofence.checkin_radius)
	accuracy_value = _to_float(accuracy)
	if accuracy_value is not None and accuracy_value > radius:
		return PresenceResult(STATUS_UNCONFIRMED, reason="low_accuracy")

	distance = get_distance_between_coordinates(
		float(geofence.latitude), float(geofence.longitude), coordinates[0], coordinates[1]
	)
	if distance > radius:
		return PresenceResult(STATUS_UNCONFIRMED, reason="too_far", distance=distance)
	return PresenceResult(STATUS_OK, EVIDENCE_GPS, distance=distance)
