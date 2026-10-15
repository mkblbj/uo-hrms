"""Exercise Nemo's HTTP boundary and actual WAV/manifest outputs."""

import io
import json
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from hrms.utils import attendance_sign_prepare as prepare


def make_wav(*, channels=1, rate=16000, seconds=1):
	buffer = io.BytesIO()
	with wave.open(buffer, "wb") as stream:
		stream.setnchannels(channels)
		stream.setsampwidth(2)
		stream.setframerate(rate)
		stream.writeframes(b"\0\0" * channels * rate * seconds)
	return buffer.getvalue()


class TestAttendanceSignPrepare(unittest.TestCase):
	def setUp(self):
		self.temp = tempfile.TemporaryDirectory()
		self.root = Path(self.temp.name)
		self.csv = self.root / "employees.csv"
		self.csv.write_text(
			"employee_id,employee_name,spoken_name\nHR-EMP-example,山田太郎,ヤマダ\n", encoding="utf-8"
		)
		self.requests = []
		self.audio = make_wav()
		case = self

		class Handler(BaseHTTPRequestHandler):
			def log_message(self, *_args):
				pass

			def do_GET(self):
				self.send_response(200)
				self.end_headers()
				self.wfile.write(
					json.dumps([{"name": "女声1", "styles": [{"id": 10005, "name": "ノーマル"}]}]).encode()
				)

			def do_POST(self):
				url = urlparse(self.path)
				body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
				case.requests.append((url.path, parse_qs(url.query), body))
				self.send_response(200)
				self.end_headers()
				if url.path == "/audio_query":
					self.wfile.write(b'{"outputSamplingRate":24000,"outputStereo":false,"speedScale":1.0}')
				else:
					self.wfile.write(case.audio)

		self.server = HTTPServer(("127.0.0.1", 0), Handler)
		self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
		self.thread.start()
		self.url = f"http://127.0.0.1:{self.server.server_port}"

	def tearDown(self):
		self.server.shutdown()
		self.server.server_close()
		self.thread.join()
		self.temp.cleanup()

	def _prepare(self):
		return prepare.prepare_bundle(self.csv, self.root / "bundle", self.url, 10005)

	def test_bundle_uses_employee_id_and_action(self):
		manifest = self._prepare()
		self.assertEqual(manifest["locale"], "ja-JP")
		self.assertEqual(set(manifest["clips"]["HR-EMP-example"]), {"IN", "OUT"})
		clip = manifest["clips"]["HR-EMP-example"]["IN"]
		self.assertEqual(clip["employee_name"], "山田太郎")
		import hashlib

		self.assertEqual(clip["asset_id"], hashlib.sha256(self.audio).hexdigest())
		self.assertEqual((self.root / "bundle/audio" / (clip["asset_id"] + ".wav")).read_bytes(), self.audio)
		queries = [json.loads(body) for path, _, body in self.requests if path == "/synthesis"]
		self.assertEqual(
			[(q["outputSamplingRate"], q["outputStereo"]) for q in queries], [(16000, False)] * 2
		)

	def test_spoken_name_override_keeps_display_name(self):
		self.csv.write_text("employee_id,employee_name,spoken_name\nHR-EMP-example,山田太郎,ヤマダさん\n")
		self._prepare()
		texts = [query["text"][0] for path, query, _ in self.requests if path == "/audio_query"]
		self.assertEqual(texts, ["ヤマダさん、おはようございます。", "ヤマダさん、お疲れさまでした。"])

	def test_invalid_rows_rejected_before_any_synthesis(self):
		for rows in (
			"HR-EMP-example,山田太郎,\n",
			"HR-EMP-example,山田太郎,ヤマダ\nHR-EMP-example,別人,サトウ\n",
		):
			with self.subTest(rows=rows):
				self.csv.write_text("employee_id,employee_name,spoken_name\n" + rows)
				with self.assertRaises(ValueError):
					self._prepare()
				self.assertEqual(self.requests, [])

	def test_invalid_wav_is_rejected_without_replacing_manifest(self):
		bundle = self.root / "bundle"
		bundle.mkdir()
		manifest_path = bundle / "manifest.json"
		manifest_path.write_text('{"old":"keep"}')
		for audio in (b"not wav", make_wav(seconds=6), make_wav(channels=2), make_wav(rate=24000)):
			with self.subTest(length=len(audio)):
				self.audio = audio
				with self.assertRaises(ValueError):
					self._prepare()
				self.assertEqual(manifest_path.read_text(), '{"old":"keep"}')

	def test_requested_speaker_must_exist(self):
		with self.assertRaises(ValueError):
			prepare.prepare_bundle(self.csv, self.root / "bundle", self.url, 999)
		self.assertEqual(self.requests, [])
