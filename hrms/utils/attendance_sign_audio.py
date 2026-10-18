"""Prepared WAV bundles kept outside public files. No synthesis on the punch path."""

import hashlib
import io
import json
import os
import re
import tempfile
import wave
from pathlib import Path

import frappe

ASSET_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
SAMPLE_RATE = 24000
MAX_WAV_BYTES = 256 * 1024


def validate_wav(data: bytes) -> None:
	if len(data) > MAX_WAV_BYTES:
		raise ValueError("Greeting WAV exceeds the 5-second size budget")
	try:
		with wave.open(io.BytesIO(data), "rb") as stream:
			frames = stream.getnframes()
			if (
				stream.getnchannels(),
				stream.getsampwidth(),
				stream.getframerate(),
				stream.getcomptype(),
			) != (1, 2, SAMPLE_RATE, "NONE"):
				raise ValueError("Greeting must be mono 16-bit PCM WAV at 24000 Hz")
			if not 0 < frames <= SAMPLE_RATE * 5 or len(stream.readframes(frames)) != frames * 2:
				raise ValueError("Greeting WAV must contain at most 5 seconds of complete audio")
	except (wave.Error, EOFError) as exc:
		raise ValueError("Invalid greeting WAV") from exc


def _store_path() -> Path:
	return Path(frappe.get_site_path("private", "attendance-sign"))


def _read_manifest(root: Path) -> dict:
	try:
		manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
		if (
			manifest.get("version") == 1
			and manifest.get("locale") == "ja-JP"
			and isinstance(manifest.get("clips"), dict)
		):
			return manifest
	except (OSError, ValueError, AttributeError):
		pass
	return {"version": 1, "locale": "ja-JP", "clips": {}}


def _atomic_write(path: Path, data: bytes) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
		temporary = Path(stream.name)
		try:
			stream.write(data)
			stream.flush()
		finally:
			stream.close()
	try:
		os.replace(temporary, path)
	finally:
		temporary.unlink(missing_ok=True)


def write_bundle(root: Path, manifest: dict, assets: dict[str, bytes]) -> None:
	"""Publish the manifest last so a failed operation leaves the old bundle usable."""
	for asset_id, data in assets.items():
		_atomic_write(root / "audio" / f"{asset_id}.wav", data)
	_atomic_write(
		root / "manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
	)


def install_bundle(source_dir: str) -> dict:
	frappe.only_for("System Manager")
	return publish_bundle(source_dir)


def _merge_employee(manifest: dict, destination: Path, employee_id: str) -> dict:
	if set(manifest["clips"]) != {employee_id}:
		raise ValueError("A single-employee bundle must contain exactly that employee")
	current = _read_manifest(destination)
	old_source = current.get("source", {})
	new_source = manifest.get("source", {})
	profiles = dict(old_source.get("profiles", {}))
	personal = dict(old_source.get("employee_voices", {}))
	if current["clips"] and not profiles and not personal:
		# Preserve a legacy single-voice bundle's attribution, including old 16k assets.
		profiles["default"] = {
			k: old_source[k]
			for k in (
				"engine",
				"speaker_id",
				"speed",
				"intonation",
				"pitch",
				"voice",
				"credit",
				"sample_rate",
			)
			if k in old_source
		}
	for voice in [*profiles.values(), *personal.values()]:
		voice.setdefault("sample_rate", old_source.get("sample_rate"))
	group = manifest["clips"][employee_id]["IN"].get("voice_group", "default")
	voice = new_source.get("employee_voices", {}).get(employee_id) or new_source.get("profiles", {}).get(
		group
	)
	if not voice:
		raise ValueError("Selected employee voice metadata is missing")
	personal[employee_id] = {**voice, "sample_rate": new_source.get("sample_rate")}
	current["clips"][employee_id] = {
		kind: {**clip, "voice_group": "personal"} for kind, clip in manifest["clips"][employee_id].items()
	}
	used_groups = {
		clip.get("voice_group", "default") for clips in current["clips"].values() for clip in clips.values()
	}
	profiles = {group: voice for group, voice in profiles.items() if group in used_groups}
	personal = {
		employee: voice
		for employee, voice in personal.items()
		if any(c.get("voice_group") == "personal" for c in current["clips"].get(employee, {}).values())
	}
	used = [*profiles.values(), *personal.values()]
	rates = {v.get("sample_rate") for v in used}
	current["source"] = {
		**new_source,
		**old_source,
		"voice": "员工分别发布",
		"profiles": profiles,
		"employee_voices": personal,
		"credit": " / ".join(sorted({v["credit"] for v in used if v.get("credit")})),
		"sample_rate": rates.pop() if len(rates) == 1 else None,
	}
	return current


def publish_bundle(
	source_dir: str, *, destination: Path | None = None, employee_id: str | None = None
) -> dict:
	"""Internal validated publisher; callers must enforce administrator access."""
	source = Path(source_dir)
	manifest = _read_manifest(source)
	if not manifest["clips"]:
		raise ValueError("A version-1 ja-JP greeting manifest is required")
	assets = {}
	count = 0
	for employee, clips in manifest["clips"].items():
		if (
			not isinstance(employee, str)
			or not employee
			or not isinstance(clips, dict)
			or set(clips) != {"IN", "OUT"}
		):
			raise ValueError("Each employee must have IN and OUT greetings")
		for clip in clips.values():
			if (
				not isinstance(clip, dict)
				or not isinstance(clip.get("employee_name"), str)
				or not clip["employee_name"].strip()
			):
				raise ValueError("Greeting display name is required")
			asset_id = clip.get("asset_id")
			if not isinstance(asset_id, str) or not ASSET_PATTERN.fullmatch(asset_id):
				raise ValueError("Invalid greeting asset ID")
			path = source / "audio" / f"{asset_id}.wav"
			if path.stat().st_size > MAX_WAV_BYTES:
				raise ValueError("Greeting WAV too large")
			data = path.read_bytes()
			validate_wav(data)
			if hashlib.sha256(data).hexdigest() != asset_id:
				raise ValueError("Greeting WAV hash does not match manifest")
			assets[asset_id] = data
			count += 1
	destination = destination or _store_path()
	if employee_id:
		manifest = _merge_employee(manifest, destination, employee_id)
	write_bundle(destination, manifest, assets)
	return {"clips": count, "assets": len(assets), "locale": "ja-JP"}


def find_clip(employee_id: str, employee_name: str, log_type: str) -> str | None:
	clip = _read_manifest(_store_path())["clips"].get(employee_id, {}).get(log_type, {})
	asset_id = clip.get("asset_id")
	if (
		clip.get("employee_name") == employee_name
		and isinstance(asset_id, str)
		and ASSET_PATTERN.fullmatch(asset_id)
	):
		if (_store_path() / "audio" / f"{asset_id}.wav").is_file():
			return asset_id
	return None


def read_asset(asset_id: str) -> bytes:
	if not isinstance(asset_id, str) or not ASSET_PATTERN.fullmatch(asset_id):
		raise frappe.DoesNotExistError("Greeting audio not found")
	manifest = _read_manifest(_store_path())
	referenced = any(
		clip.get("asset_id") == asset_id for clips in manifest["clips"].values() for clip in clips.values()
	)
	if not referenced:
		raise frappe.DoesNotExistError("Greeting audio not found")
	try:
		return (_store_path() / "audio" / f"{asset_id}.wav").read_bytes()
	except FileNotFoundError as exc:
		raise frappe.DoesNotExistError("Greeting audio not found") from exc
