"""Private draft -> preview -> generation -> explicit publish for attendance voices."""

import contextlib
import fcntl
import hashlib
import json
import time
import uuid
from pathlib import Path

import frappe

from hrms.utils.attendance_sign_audio import SAMPLE_RATE, _atomic_write, validate_wav, write_bundle


def _root():
	return Path(frappe.get_site_path("private", "attendance-voice-settings"))


def _active_root():
	return Path(frappe.get_site_path("private", "attendance-sign"))


@contextlib.contextmanager
def _lock():
	_root().mkdir(parents=True, exist_ok=True)
	with (_root() / "settings.lock").open("a") as stream:
		fcntl.flock(stream, fcntl.LOCK_EX)
		try:
			yield
		finally:
			fcntl.flock(stream, fcntl.LOCK_UN)


def _json(path, default):
	try:
		return json.loads(path.read_text(encoding="utf-8"))
	except (OSError, ValueError):
		return default


def _surname(name, last_name=""):
	if last_name and last_name.strip():
		return last_name.strip()
	name = name.strip()
	if " " in name:
		return name.split()[0]
	compounds = {
		"欧阳",
		"歐陽",
		"司马",
		"司馬",
		"上官",
		"诸葛",
		"諸葛",
		"夏侯",
		"皇甫",
		"尉迟",
		"尉遲",
		"公孙",
		"公孫",
		"司徒",
		"司空",
		"慕容",
		"令狐",
		"南宫",
		"南宮",
		"独孤",
		"獨孤",
		"东方",
		"東方",
		"长孙",
		"長孫",
	}
	return name[:2] if name[:2] in compounds else name[:1]


def _employees():
	return [
		{
			"name": e.name,
			"employee_name": e.employee_name,
			"surname": _surname(e.employee_name, e.last_name or ""),
		}
		for e in frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name", "last_name"],
			order_by="employee_name asc, name asc",
		)
	]


def _read():
	published = _json(_active_root() / "manifest.json", {})
	source = published.get("source", {})
	engine = "nemo" if "Nemo" in source.get("engine", "Nemo") else "voicevox"
	default = {
		"revision": 0,
		"draft": {
			"engine": engine,
			"speaker_id": source.get("speaker_id", 10005 if engine == "nemo" else 2),
			"speed": 1.0,
			"readings": {},
		},
		"generation": None,
		"published_revision": None,
	}
	return _json(_root() / "settings.json", default)


def _write(state):
	_atomic_write(
		_root() / "settings.json", (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode()
	)


def _normal(config):
	if isinstance(config, str):
		config = json.loads(config)
	if not isinstance(config, dict) or config.get("engine") not in ("nemo", "voicevox"):
		frappe.throw("请选择有效的语音引擎")
	try:
		speaker = int(config["speaker_id"])
		speed = float(config.get("speed", 1))
	except (KeyError, TypeError, ValueError):
		frappe.throw("请选择音色并填写有效语速")
	if not 0 <= speaker <= 1000000 or not 0.5 <= speed <= 2:
		frappe.throw("语速需在 0.5～2.0 之间")
	readings = config.get("readings", {})
	if not isinstance(readings, dict):
		frappe.throw("姓氏读音格式不正确")
	valid = {e["name"] for e in _employees()}
	cleaned = {}
	for employee, text in readings.items():
		if employee not in valid:
			# A saved reading for someone who left must not block the remaining staff.
			continue
		if not isinstance(text, str) or len(text) > 80 or any(c in text for c in "\r\n\0"):
			frappe.throw("姓氏读音需为80字以内的单行文字")
		if text.strip():
			cleaned[employee] = text.strip()
	return {"engine": config["engine"], "speaker_id": speaker, "speed": speed, "readings": cleaned}


def _fingerprint(config, employees):
	return hashlib.sha256(
		json.dumps([config, employees, SAMPLE_RATE], ensure_ascii=False, sort_keys=True).encode()
	).hexdigest()


def get_settings():
	with _lock():
		state = _read()
	employees = _employees()
	generation = state.get("generation")
	public = None
	if generation:
		public = {k: generation.get(k) for k in ("id", "status", "done", "total", "error")}
		if public["status"] in ("queued", "running") and time.time() - generation.get("started_at", 0) > 600:
			public["status"] = "error"
			public["error"] = "生成任务已超时，请重新生成"
		public["can_publish"] = public["status"] == "ready" and generation["fingerprint"] == _fingerprint(
			state["draft"], employees
		)
	active = _json(_active_root() / "manifest.json", {})
	return {
		"revision": state["revision"],
		"draft": state["draft"],
		"employees": employees,
		"generation": public,
		"published": {
			"source": active.get("source", {}),
			"employees": len(active.get("clips", {})),
			"revision": state.get("published_revision"),
		},
	}


def save_settings(config, revision):
	config = _normal(config)
	with _lock():
		state = _read()
		if int(revision) != state["revision"]:
			frappe.throw("设置已被其他窗口修改，请刷新后重试")
		state["revision"] += 1
		state["draft"] = config
		_write(state)
	return get_settings()


def _render(config, text):
	from hrms.utils.attendance_voice_engine import render

	return render(config["engine"], config["speaker_id"], text, config["speed"])


def _text(config, employee, kind):
	spoken = config["readings"].get(employee["name"]) or employee["surname"]
	if spoken.endswith("さん"):
		spoken = spoken[:-2]
	return f"{spoken}さん、" + ("おはようございます。" if kind == "IN" else "お疲れさまでした。")


def _render_for(config, employee, kind):
	text = _text(config, employee, kind)
	result = _render(config, text)
	try:
		validate_wav(result["audio"])
	except ValueError as exc:
		raise frappe.ValidationError(
			f"{employee['employee_name']} 的语音需在5秒内，请提高语速或缩短姓氏读音"
		) from exc
	return text, result


def preview(config, employee_id, kind):
	config = _normal(config)
	employee = next((e for e in _employees() if e["name"] == employee_id), None)
	if not employee or kind not in ("IN", "OUT"):
		frappe.throw("请选择有效员工与签到或签退")
	text, result = _render_for(config, employee, kind)
	asset = hashlib.sha256(result["audio"]).hexdigest()
	_atomic_write(_root() / "previews" / f"{asset}.wav", result["audio"])
	return {
		"url": f"/api/method/hrms.api.attendance_voice_settings.get_preview_audio?asset_id={asset}",
		"text": text,
		"credit": result["credit"],
	}


def preview_audio(asset):
	from hrms.utils.attendance_sign_audio import ASSET_PATTERN

	if not isinstance(asset, str) or not ASSET_PATTERN.fullmatch(asset):
		raise frappe.DoesNotExistError("试听文件不存在")
	try:
		return (_root() / "previews" / f"{asset}.wav").read_bytes()
	except FileNotFoundError as exc:
		raise frappe.DoesNotExistError("试听文件不存在，请重新试听") from exc


def _enqueue(request_id):
	frappe.enqueue(
		"hrms.utils.attendance_voice_settings.generate_job",
		queue=frappe.conf.get("attendance_voice_queue") or "default",
		timeout=600,
		enqueue_after_commit=True,
		job_id="attendance-voice-" + request_id,
		request_id=request_id,
	)


def start_generation(revision):
	employees = _employees()
	if not employees:
		frappe.throw("没有在职员工可生成语音")
	with _lock():
		state = _read()
		if int(revision) != state["revision"]:
			frappe.throw("草稿已变化，请先保存草稿")
		old = state.get("generation")
		if old and old["status"] in ("queued", "running") and time.time() - old["started_at"] < 600:
			frappe.throw("已有生成任务，请等待完成")
		request_id = uuid.uuid4().hex
		generation = {
			"id": request_id,
			"status": "queued",
			"done": 0,
			"total": len(employees) * 2,
			"error": None,
			"started_at": time.time(),
			"fingerprint": _fingerprint(state["draft"], employees),
			"config": state["draft"],
			"employees": employees,
		}
		state["generation"] = generation
		_write(state)
	try:
		_enqueue(request_id)
	except Exception:
		with _lock():
			state = _read()
			if state["generation"]["id"] == request_id:
				state["generation"].update(status="error", error="任务队列暂不可用，请稍后重新生成")
				_write(state)
		raise
	return {"id": request_id}


def _progress(request_id, **values):
	with _lock():
		state = _read()
		if not state.get("generation") or state["generation"]["id"] != request_id:
			return False
		state["generation"].update(values)
		_write(state)
		return True


def generate_job(request_id):
	with _lock():
		state = _read()
		generation = state.get("generation")
	if not generation or generation["id"] != request_id:
		return
	_progress(request_id, status="running")
	try:
		config = generation["config"]
		assets = {}
		clips = {}
		done = 0
		source = {}
		for employee in generation["employees"]:
			clips[employee["name"]] = {}
			for kind in ("IN", "OUT"):
				_, result = _render_for(config, employee, kind)
				asset = hashlib.sha256(result["audio"]).hexdigest()
				assets[asset] = result["audio"]
				clips[employee["name"]][kind] = {
					"asset_id": asset,
					"employee_name": employee["employee_name"],
				}
				source = {
					"engine": "VOICEVOX Nemo" if config["engine"] == "nemo" else "VOICEVOX",
					"speaker_id": config["speaker_id"],
					"voice": result["voice"],
					"credit": result["credit"],
					"sample_rate": SAMPLE_RATE,
					"name_readings": "surname-only administrator draft",
					"checkin_greeting": "おはようございます。",
					"checkout_greeting": "お疲れさまでした。",
				}
				done += 1
				if not _progress(request_id, done=done):
					return
		manifest = {"version": 1, "locale": "ja-JP", "source": source, "clips": clips}
		write_bundle(_root() / "generations" / request_id, manifest, assets)
		_progress(request_id, status="ready", error=None)
	except Exception as exc:
		_progress(request_id, status="error", error="生成失败：" + str(exc)[:220])


def publish(request_id):
	employees = _employees()
	with _lock():
		state = _read()
		generation = state.get("generation")
		if not generation or generation["id"] != request_id or generation["status"] != "ready":
			frappe.throw("请先完成生成，再发布")
		if generation["fingerprint"] != _fingerprint(state["draft"], employees):
			frappe.throw("草稿、员工资料或音频规格已变化，请重新生成后发布")
		# Validated bundle publication is shared with the existing admin CLI.
		from hrms.utils.attendance_sign_audio import publish_bundle

		publish_bundle(str(_root() / "generations" / request_id), destination=_active_root())
		generation["status"] = "published"
		state["published_revision"] = state["revision"]
		_write(state)
	return get_settings()
