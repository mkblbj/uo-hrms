import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import frappe

from hrms.tests.test_attendance_voice_settings import wav
from hrms.utils import attendance_voice_engine as engine


class TestAttendanceVoiceEngine(unittest.TestCase):
	def setUp(self):
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name)
		self.root_patch = patch.object(engine, "_control_root", return_value=self.root)
		self.root_patch.start()

	def tearDown(self):
		self.root_patch.stop()
		self.tmp.cleanup()

	def test_invalid_engine_cannot_create_lease(self):
		with self.assertRaises(ValueError):
			engine.lease("../arbitrary-service")
		self.assertFalse((self.root / "engine-lease.json").exists())

	def test_lease_and_idle_release_have_bounded_lifetime(self):
		with patch.object(engine.time, "time", return_value=100):
			engine.lease("voicevox")
		data = json.loads((self.root / "engine-lease.json").read_text())
		self.assertEqual(data["engine"], "voicevox")
		self.assertEqual(data["expires_at"], 190)
		with patch.object(engine.time, "time", return_value=110):
			engine.release("voicevox")
		self.assertEqual(json.loads((self.root / "engine-lease.json").read_text())["expires_at"], 170)

	def test_catalog_has_correct_attribution(self):
		speakers = [{"name": "四国めたん", "styles": [{"id": 2, "name": "ノーマル"}]}]
		with patch.object(engine, "_wait"), patch.object(engine, "_json_request", return_value=speakers):
			catalog = engine.get_catalog("voicevox")
		self.assertEqual(catalog[0]["credit"], "VOICEVOX:四国めたん")
		self.assertEqual(catalog[0]["id"], 2)

	def test_render_requests_pcm_format_and_correct_voice(self):
		calls = []

		def request(url, payload=None, post=False):
			calls.append((url, payload, post))
			if "/speakers" in url:
				return json.dumps(
					[{"name": "四国めたん", "styles": [{"id": 2, "name": "ノーマル"}]}]
				).encode()
			if "/audio_query" in url:
				return b"{}"
			return wav()

		with patch.object(engine, "_wait"), patch.object(engine, "_request", side_effect=request):
			result = engine.render("voicevox", 2, "ワンさん、おはようございます。", 1.1)
		self.assertEqual(result["audio"], wav())
		body = json.loads(next(x[1] for x in calls if "/synthesis" in x[0]))
		self.assertEqual(
			(body["outputSamplingRate"], body["outputStereo"], body["speedScale"]), (24000, False, 1.1)
		)

	def test_overlong_speech_has_actionable_chinese_error(self):
		with (
			patch.object(engine, "_wait"),
			patch.object(engine, "_catalog", return_value=[{"id": 2}]),
			patch.object(engine, "_request", side_effect=[b"{}", wav(6)]),
		):
			with self.assertRaisesRegex(frappe.ValidationError, "5秒.*提高语速"):
				engine.render("voicevox", 2, "ワンさん、おはようございます。", 1)


class TestHostVoiceWorker(unittest.TestCase):
	def test_only_valid_live_leases_start_and_expired_services_stop(self):
		module_path = Path(__file__).resolve().parents[2] / "deploy/attendance_voice_engine_worker.py"
		spec = importlib.util.spec_from_file_location("host_voice_worker", module_path)
		worker_module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(worker_module)
		with tempfile.TemporaryDirectory() as tmp:
			root = Path(tmp)
			lease = root / "site/private/attendance-voice-settings/engine-lease.json"
			lease.parent.mkdir(parents=True)
			lease.write_text(json.dumps({"engine": "voicevox", "expires_at": 200}))
			calls = []
			worker = worker_module.EngineWorker(
				[root], root / "compose.yaml", gpu=True, runner=lambda args: calls.append(args)
			)
			worker.started = {}
			worker.initial = False
			worker.tick(100)
			self.assertTrue(any("up" in args and args[-1] == "voicevox-gpu" for args in calls))
			worker.tick(201)
			self.assertTrue(any("stop" in args and args[-1] == "voicevox-gpu" for args in calls))
			calls.clear()
			lease.write_text(json.dumps({"engine": "evil; touch /tmp/pwn", "expires_at": 999}))
			worker.tick(300)
			self.assertEqual(calls, [])
