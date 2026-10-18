"""Only the fixed private TTS endpoints; a host lease worker owns Docker access."""

import contextlib
import fcntl
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import frappe

from hrms.utils.attendance_sign_audio import SAMPLE_RATE, _atomic_write, validate_wav

ENGINES = {"nemo": "http://attendance-sign-nemo:50121", "voicevox": "http://attendance-sign-voicevox:50021"}


def _control_root():
	return Path(frappe.get_site_path("private", "attendance-voice-settings"))


def _endpoint(engine):
	if engine not in ENGINES:
		raise ValueError("请选择有效语音引擎")
	return ENGINES[engine]


def lease(engine, seconds=90):
	_endpoint(engine)
	_atomic_write(
		_control_root() / "engine-lease.json",
		json.dumps({"engine": engine, "expires_at": time.time() + seconds}).encode(),
	)


def release(engine):
	lease(engine, 60)


@contextlib.contextmanager
def _session(engine):
	_endpoint(engine)
	_control_root().mkdir(parents=True, exist_ok=True)
	# Cross-site requests use the shared site-filesystem gate, not a public socket.
	path = Path(frappe.local.sites_path) / ".attendance-voice-engine.lock"
	with path.open("a") as lock:
		try:
			fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
		except BlockingIOError as exc:
			raise frappe.ValidationError("语音引擎正在处理其他任务，请稍后再试") from exc
		try:
			lease(engine)
			_wait(engine)
			yield
		finally:
			release(engine)
			fcntl.flock(lock, fcntl.LOCK_UN)


def _request(url, payload=None, post=False):
	request = Request(url, data=payload, method="POST" if post else "GET")
	if payload is not None:
		request.add_header("Content-Type", "application/json")
	with urlopen(request, timeout=45) as r:
		return r.read()


def _json_request(url):
	return json.loads(_request(url))


def _wait(engine):
	for _ in range(55):
		try:
			_json_request(_endpoint(engine) + "/version")
			return
		except (OSError, ValueError):
			time.sleep(1)
	raise RuntimeError("语音服务启动超时，请稍后重试或联系管理员")


def _catalog(engine):
	speakers = _json_request(_endpoint(engine) + "/speakers")
	return [
		{
			"id": style["id"],
			"name": speaker["name"],
			"style": style["name"],
			"credit": "VOICEVOX Nemo" if engine == "nemo" else "VOICEVOX:" + speaker["name"],
		}
		for speaker in speakers
		for style in speaker["styles"]
		if style.get("type", "talk") == "talk"
	]


def get_catalog(engine):
	_endpoint(engine)
	path = _control_root() / f"catalog-{engine}.json"
	if path.exists():
		return json.loads(path.read_text())
	with _session(engine):
		catalog = _catalog(engine)
	_atomic_write(path, json.dumps(catalog, ensure_ascii=False).encode())
	return catalog


def render(engine, speaker_id, text, speed, intonation=1.0, pitch=0.0):
	with _session(engine):
		catalog = _catalog(engine)
		voice = next((v for v in catalog if v["id"] == speaker_id), None)
		if voice is None:
			raise ValueError("所选音色已不可用，请重新选择")
		query = json.loads(
			_request(
				_endpoint(engine) + "/audio_query?" + urlencode({"speaker": speaker_id, "text": text}),
				post=True,
			)
		)
		query.update(
			outputSamplingRate=SAMPLE_RATE,
			outputStereo=False,
			speedScale=speed,
			intonationScale=intonation,
			pitchScale=pitch,
		)
		audio = _request(
			_endpoint(engine) + "/synthesis?" + urlencode({"speaker": speaker_id}),
			json.dumps(query).encode(),
			post=True,
		)
		try:
			validate_wav(audio)
		except ValueError as exc:
			raise frappe.ValidationError("语音需为5秒内的完整音频，请提高语速或缩短朗读内容") from exc
		return {"audio": audio, "voice": voice["name"] + " / " + voice["style"], "credit": voice["credit"]}
