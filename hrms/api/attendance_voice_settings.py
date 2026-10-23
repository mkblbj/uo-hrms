"""Authenticated Chinese Desk voice-settings API. Never exposes device credentials."""

import frappe

from hrms.utils import attendance_voice_settings as service


def _require_manager():
	frappe.only_for(("System Manager", "HR Manager"))


@frappe.whitelist(methods=["GET", "POST"])
def get_settings():
	_require_manager()
	return service.get_settings()


@frappe.whitelist(methods=["POST"])
def save_settings(config: str, revision: int):
	_require_manager()
	return service.save_settings(config, revision)


@frappe.whitelist(methods=["POST"])
def get_voices(engine: str):
	_require_manager()
	from hrms.utils.attendance_voice_engine import get_catalog

	return get_catalog(engine)


@frappe.whitelist(methods=["POST"])
def preview(config: str, employee_id: str, kind: str = "IN"):
	_require_manager()
	return service.preview(config, employee_id, kind)


@frappe.whitelist(methods=["GET"])
def get_preview_audio(asset_id: str):
	_require_manager()
	data = service.preview_audio(asset_id)
	frappe.local.response_headers["Cache-Control"] = "no-store"
	frappe.response.update(
		type="download",
		filename="preview.wav",
		filecontent=data,
		content_type="audio/wav",
		display_content_as="inline",
	)


@frappe.whitelist(methods=["POST"])
def start_generation(revision: int, employee_id: str | None = None):
	_require_manager()
	return service.start_generation(revision, employee_id)


@frappe.whitelist(methods=["POST"])
def publish(request_id: str):
	_require_manager()
	return service.publish(request_id)
