"""Administrator draft/preview/generate/publish behavior, using real private files."""

import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import frappe

from hrms.api import attendance_voice_settings as api
from hrms.utils import attendance_voice_settings as service


def wav(seconds=1):
	out = io.BytesIO()
	with wave.open(out, "wb") as f:
		f.setnchannels(1)
		f.setsampwidth(2)
		f.setframerate(24000)
		f.writeframes(b"\0\0" * 24000 * seconds)
	return out.getvalue()


class TestAttendanceVoiceSettings(unittest.TestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.tmp = tempfile.TemporaryDirectory()
		self.root = Path(self.tmp.name)
		self.patches = [
			patch.object(service, "_root", return_value=self.root / "settings"),
			patch.object(service, "_active_root", return_value=self.root / "active"),
			patch.object(
				service,
				"_employees",
				return_value=[{"name": "EMP-voice", "employee_name": "王小明", "surname": "王"}],
			),
		]
		for p in self.patches:
			p.start()
		self.config = {"engine": "nemo", "speaker_id": 10005, "speed": 1.0, "readings": {"EMP-voice": "ワン"}}

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()
		self.tmp.cleanup()
		frappe.set_user("Administrator")

	def save(self):
		return api.save_settings(json.dumps(self.config), 0)

	def fake_render(self, *args):
		return {"audio": wav(), "voice": "女声1 / 自然", "credit": "VOICEVOX Nemo"}

	def test_guest_cannot_use_any_management_api(self):
		frappe.set_user("Guest")
		for method, args in [
			(api.get_settings, ()),
			(api.save_settings, (json.dumps(self.config), 0)),
			(api.get_voices, ("nemo",)),
			(api.preview, (json.dumps(self.config), "EMP-voice", "IN")),
			(api.start_generation, (1,)),
			(api.publish, ("a" * 32,)),
			(api.get_preview_audio, ("a" * 64,)),
		]:
			with self.subTest(method=method.__name__), self.assertRaises(frappe.PermissionError):
				method(*args)

	def test_draft_persists_and_rejects_stale_save(self):
		saved = self.save()
		self.assertEqual(saved["revision"], 1)
		loaded = api.get_settings()
		self.assertEqual(loaded["draft"]["readings"]["EMP-voice"], "ワン")
		self.assertEqual(loaded["employees"][0]["employee_name"], "王小明")
		with self.assertRaises(frappe.ValidationError):
			api.save_settings(json.dumps(self.config), 0)

	def test_hr_manager_can_edit_but_employee_cannot(self):
		frappe.set_user("Guest")
		with patch.object(frappe, "get_roles", return_value=["HR Manager"]):
			self.assertEqual(self.save()["revision"], 1)
		with patch.object(frappe, "get_roles", return_value=["Employee"]):
			with self.assertRaises(frappe.PermissionError):
				api.get_settings()

	def test_preview_uses_only_surname_and_never_publishes(self):
		with patch.object(service, "_render", side_effect=self.fake_render) as render:
			result = api.preview(json.dumps(self.config), "EMP-voice", "IN")
		self.assertEqual(render.call_args.args[1], "ワンさん、おはようございます。")
		self.assertIn("get_preview_audio", result["url"])
		self.assertFalse((self.root / "active/manifest.json").exists())
		self.assertEqual(api.get_settings()["revision"], 0)

	def test_empty_reading_falls_back_to_surname(self):
		self.config["readings"] = {}
		with patch.object(service, "_render", side_effect=self.fake_render) as render:
			api.preview(json.dumps(self.config), "EMP-voice", "OUT")
		self.assertEqual(render.call_args.args[1], "王さん、お疲れさまでした。")

	def test_surname_uses_employee_last_name_and_handles_compound_surname(self):
		self.assertEqual(service._surname("王小明", "王"), "王")
		self.assertEqual(service._surname("欧阳小雨"), "欧阳")
		self.assertEqual(service._surname("山田太郎", "山田"), "山田")

	def test_departed_employee_reading_does_not_block_saving_remaining_staff(self):
		self.config["readings"]["EMP-departed"] = "リー"
		saved = self.save()
		self.assertEqual(saved["draft"]["readings"], {"EMP-voice": "ワン"})

	def run_generation(self):
		self.save()
		with patch.object(service, "_enqueue"):
			job = api.start_generation(1)
		with patch.object(service, "_render", side_effect=self.fake_render):
			service.generate_job(job["id"])
		return job["id"]

	def test_generation_is_not_published_until_explicit_publish(self):
		job = self.run_generation()
		self.assertFalse((self.root / "active/manifest.json").exists())
		self.assertEqual(api.get_settings()["generation"]["status"], "ready")
		api.publish(job)
		active = json.loads((self.root / "active/manifest.json").read_text())
		self.assertEqual(set(active["clips"]["EMP-voice"]), {"IN", "OUT"})
		self.assertEqual(api.get_settings()["generation"]["status"], "published")

	def test_changed_draft_cannot_publish_stale_generation(self):
		job = self.run_generation()
		self.config["readings"]["EMP-voice"] = "オウ"
		api.save_settings(json.dumps(self.config), 1)
		with self.assertRaises(frappe.ValidationError):
			api.publish(job)
		self.assertFalse((self.root / "active/manifest.json").exists())

	def test_pre_upgrade_generation_is_not_publishable_at_new_sample_rate(self):
		import hashlib

		self.save()
		state = service._read()
		legacy_fingerprint = hashlib.sha256(
			json.dumps([state["draft"], service._employees()], ensure_ascii=False, sort_keys=True).encode()
		).hexdigest()
		state["generation"] = {"id": "a" * 32, "status": "ready", "fingerprint": legacy_fingerprint}
		service._write(state)
		self.assertFalse(api.get_settings()["generation"]["can_publish"])
		with self.assertRaisesRegex(frappe.ValidationError, "重新生成"):
			api.publish("a" * 32)

	def test_renamed_employee_cannot_publish_stale_generation(self):
		job = self.run_generation()
		with patch.object(
			service,
			"_employees",
			return_value=[{"name": "EMP-voice", "employee_name": "王新名", "surname": "王"}],
		):
			with self.assertRaises(frappe.ValidationError):
				api.publish(job)

	def test_generation_failure_keeps_current_audio(self):
		job = self.run_generation()
		api.publish(job)
		before = (self.root / "active/manifest.json").read_bytes()
		with patch.object(service, "_enqueue"):
			job = api.start_generation(1)
		with patch.object(service, "_render", side_effect=RuntimeError("engine unavailable")):
			service.generate_job(job["id"])
		self.assertEqual(api.get_settings()["generation"]["status"], "error")
		self.assertEqual((self.root / "active/manifest.json").read_bytes(), before)

	def test_invalid_preview_and_asset_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			api.preview(json.dumps(self.config), "unknown", "IN")
		with self.assertRaises(frappe.ValidationError):
			api.preview(json.dumps(self.config), "EMP-voice", "DELETE")
		with self.assertRaises(frappe.DoesNotExistError):
			api.get_preview_audio("../../site_config.json")

	def profiles(self):
		return {
			"male": {"engine": "voicevox", "speaker_id": 13, "speed": 0.9, "intonation": 0.0},
			"female": {"engine": "nemo", "speaker_id": 10005, "speed": 1.1, "intonation": 1.4},
		}

	def staff(self, gender):
		return [{"name": "EMP-voice", "employee_name": "王小明", "surname": "王", "gender": gender}]

	def test_legacy_draft_expands_independent_profiles_without_writing(self):
		service._write({"revision": 3, "draft": self.config, "generation": None, "published_revision": None})
		path = self.root / "settings/settings.json"
		before = path.read_bytes()
		draft = api.get_settings()["draft"]
		self.assertEqual(draft["profiles"]["male"]["speaker_id"], 10005)
		self.assertEqual(draft["profiles"]["female"]["intonation"], 1.0)
		draft["profiles"]["male"]["speaker_id"] = 13
		self.assertEqual(draft["profiles"]["female"]["speaker_id"], 10005)
		self.assertEqual(path.read_bytes(), before)

	def test_profiles_and_intonation_persist_independently(self):
		self.config["profiles"] = self.profiles()
		self.save()
		draft = api.get_settings()["draft"]
		self.assertEqual(draft["profiles"], self.profiles())
		self.assertEqual(draft["readings"], {"EMP-voice": "ワン"})

	def test_preview_routes_by_staff_gender_including_other_default(self):
		self.config["profiles"] = self.profiles()
		for gender, speaker, intonation in [
			("Male", 13, 0.0),
			("Female", 10005, 1.4),
			("Genderqueer", 10005, 1.0),
			("", 10005, 1.0),
		]:
			with (
				self.subTest(gender=gender),
				patch.object(service, "_employees", return_value=self.staff(gender)),
				patch.object(service, "_render", side_effect=self.fake_render) as render,
			):
				api.preview(json.dumps(self.config), "EMP-voice", "IN")
				voice = render.call_args.args[0]
				self.assertEqual((voice["speaker_id"], voice["intonation"]), (speaker, intonation))

	def test_invalid_intonation_is_rejected_for_every_profile(self):
		for group in ("default", "male", "female"):
			for value in (-0.1, 2.01, float("nan"), float("inf"), "bad"):
				config = {**self.config, "profiles": self.profiles()}
				if group == "default":
					config["intonation"] = value
				else:
					config["profiles"][group]["intonation"] = value
				with self.subTest(group=group, value=value), self.assertRaises(frappe.ValidationError):
					api.save_settings(json.dumps(config), 0)

	def test_gender_change_blocks_old_generation(self):
		with patch.object(service, "_employees", return_value=self.staff("Male")):
			job = self.run_generation()
		with patch.object(service, "_employees", return_value=self.staff("Female")):
			with self.assertRaises(frappe.ValidationError):
				api.publish(job)

	def test_generation_records_voice_group_and_attribution(self):
		self.config["profiles"] = self.profiles()
		with patch.object(service, "_employees", return_value=self.staff("Male")):
			job = self.run_generation()
		manifest = json.loads((self.root / "settings/generations" / job / "manifest.json").read_text())
		self.assertEqual(manifest["source"]["profiles"]["male"]["speaker_id"], 13)
		self.assertEqual(manifest["source"]["profiles"]["male"]["intonation"], 0.0)
		self.assertEqual(manifest["clips"]["EMP-voice"]["IN"]["voice_group"], "male")

	def test_manual_voice_group_overrides_gender_and_persists(self):
		self.config["profiles"] = self.profiles()
		self.config["voice_groups"] = {"EMP-voice": "male"}
		with patch.object(service, "_employees", return_value=self.staff("Female")):
			self.save()
			self.assertEqual(api.get_settings()["draft"]["voice_groups"], {"EMP-voice": "male"})
			with patch.object(service, "_render", side_effect=self.fake_render) as render:
				api.preview(json.dumps(self.config), "EMP-voice", "IN")
			self.assertEqual(render.call_args.args[0]["speaker_id"], 13)

	def test_invalid_manual_group_is_rejected(self):
		self.config["voice_groups"] = {"EMP-voice": "unknown"}
		with self.assertRaises(frappe.ValidationError):
			self.save()

	def test_mixed_generation_keeps_all_used_profile_attributions(self):
		self.config["profiles"] = self.profiles()
		staff = [
			{"name": "EMP-" + str(i), "employee_name": "测试员工" + str(i), "surname": "王", "gender": gender}
			for i, gender in enumerate(("Male", "Female", "Genderqueer"))
		]
		with patch.object(service, "_employees", return_value=staff):
			job = self.run_generation()
		manifest = json.loads((self.root / "settings/generations" / job / "manifest.json").read_text())
		self.assertEqual(set(manifest["source"]["profiles"]), {"male", "female", "default"})
		self.assertEqual(
			[manifest["clips"][e["name"]]["IN"]["voice_group"] for e in staff], ["male", "female", "default"]
		)
