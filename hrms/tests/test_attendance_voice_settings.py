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

	def test_generation_batches_engines_without_invalidating_employee_snapshot(self):
		self.config["profiles"] = self.profiles()
		staff = [
			{"name": "EMP-" + str(i), "employee_name": "测试" + str(i), "surname": "王", "gender": gender}
			for i, gender in enumerate(("Male", "Female", "Male", "Genderqueer"))
		]
		with patch.object(service, "_employees", return_value=staff):
			self.save()
			with patch.object(service, "_enqueue"):
				job = api.start_generation(1)
			with patch.object(service, "_render", side_effect=self.fake_render) as render:
				service.generate_job(job["id"])
			self.assertEqual(
				[call.args[0]["engine"] for call in render.call_args_list], ["nemo"] * 4 + ["voicevox"] * 4
			)
			self.assertTrue(api.get_settings()["generation"]["can_publish"])

	def personal(self, speaker=29):
		return {"engine": "voicevox", "speaker_id": speaker, "speed": 1.2, "intonation": 0.3}

	def test_personal_voice_persists_and_overrides_manual_group_for_both_greetings(self):
		self.config.update(
			profiles=self.profiles(),
			voice_groups={"EMP-voice": "female"},
			employee_voices={"EMP-voice": self.personal()},
		)
		with patch.object(service, "_employees", return_value=self.staff("Male")):
			self.save()
			draft = api.get_settings()["draft"]
			self.assertEqual(draft["employee_voices"], {"EMP-voice": self.personal()})
			self.config["profiles"]["female"]["speaker_id"] = 10001
			for kind, greeting in [("IN", "おはようございます。"), ("OUT", "お疲れさまでした。")]:
				with patch.object(service, "_render", side_effect=self.fake_render) as render:
					api.preview(json.dumps(self.config), "EMP-voice", kind)
				self.assertEqual(render.call_args.args, (self.personal(), "ワンさん、" + greeting))
		self.assertFalse((self.root / "active/manifest.json").exists())

	def test_removing_personal_voice_restores_group_without_changing_colleague(self):
		self.config.update(
			profiles=self.profiles(),
			voice_groups={"EMP-voice": "female"},
			employee_voices={"EMP-voice": self.personal()},
		)
		staff = [
			*self.staff("Male"),
			{"name": "EMP-colleague", "employee_name": "李小雨", "surname": "李", "gender": "Male"},
		]
		with patch.object(service, "_employees", return_value=staff):
			for employee, expected in [("EMP-voice", 29), ("EMP-colleague", 13)]:
				with patch.object(service, "_render", side_effect=self.fake_render) as render:
					api.preview(json.dumps(self.config), employee, "IN")
				self.assertEqual(render.call_args.args[0]["speaker_id"], expected)
			self.config["employee_voices"] = {}
			for employee, expected in [("EMP-voice", 10005), ("EMP-colleague", 13)]:
				with patch.object(service, "_render", side_effect=self.fake_render) as render:
					api.preview(json.dumps(self.config), employee, "IN")
				self.assertEqual(render.call_args.args[0]["speaker_id"], expected)

	def test_invalid_personal_voice_is_rejected_without_saving(self):
		for override in (
			[],
			{"EMP-voice": None},
			{"EMP-voice": {**self.personal(), "engine": "unknown"}},
			{"EMP-voice": {**self.personal(), "speaker_id": "bad"}},
			{"EMP-voice": {**self.personal(), "speed": 0}},
			{"EMP-voice": {**self.personal(), "intonation": float("nan")}},
		):
			with self.subTest(override=override), self.assertRaises(frappe.ValidationError):
				api.save_settings(json.dumps({**self.config, "employee_voices": override}), 0)
		self.assertEqual(api.get_settings()["revision"], 0)

	def test_departed_personal_voice_does_not_block_remaining_staff(self):
		self.config["employee_voices"] = {"EMP-voice": self.personal(), "EMP-departed": None}
		self.save()
		self.assertEqual(api.get_settings()["draft"]["employee_voices"], {"EMP-voice": self.personal()})

	def test_generation_preserves_each_personal_voice_and_all_group_credits(self):
		staff = [
			{"name": "EMP-" + str(i), "employee_name": "测试" + str(i), "surname": "王", "gender": gender}
			for i, gender in enumerate(("Male", "Male", "Male", "Female"))
		]
		self.config.update(
			profiles=self.profiles(),
			employee_voices={"EMP-0": self.personal(29), "EMP-1": self.personal(42)},
		)

		def render(voice, text):
			return {
				"audio": wav(),
				"voice": "角色" + str(voice["speaker_id"]),
				"credit": "来源" + str(voice["speaker_id"]),
			}

		with patch.object(service, "_employees", return_value=staff):
			self.save()
			with patch.object(service, "_enqueue"):
				job = api.start_generation(1)
			with patch.object(service, "_render", side_effect=render):
				service.generate_job(job["id"])
			self.assertTrue(api.get_settings()["generation"]["can_publish"])
		manifest = json.loads((self.root / "settings/generations" / job["id"] / "manifest.json").read_text())
		source = manifest["source"]
		self.assertEqual(source["profiles"]["male"]["speaker_id"], 13)
		self.assertEqual(source["profiles"]["female"]["speaker_id"], 10005)
		for employee, speaker in [("EMP-0", 29), ("EMP-1", 42)]:
			self.assertEqual(source["employee_voices"][employee]["speaker_id"], speaker)
			self.assertEqual(manifest["clips"][employee]["IN"]["voice_group"], "personal")
		self.assertEqual(set(source["credit"].split(" / ")), {"来源13", "来源29", "来源42", "来源10005"})

	def test_personal_voice_change_blocks_old_generation(self):
		self.config["employee_voices"] = {"EMP-voice": self.personal()}
		job = self.run_generation()
		self.config["employee_voices"]["EMP-voice"]["speaker_id"] = 42
		api.save_settings(json.dumps(self.config), 1)
		self.assertFalse(api.get_settings()["generation"]["can_publish"])
		with self.assertRaises(frappe.ValidationError):
			api.publish(job)

	def test_empty_personal_upgrade_keeps_legacy_ready_generation_and_file_unchanged(self):
		import hashlib

		legacy = service._expand_draft(self.config)
		legacy.pop("employee_voices", None)
		fingerprint = hashlib.sha256(
			json.dumps([legacy, service._employees(), 24000], ensure_ascii=False, sort_keys=True).encode()
		).hexdigest()
		service._write(
			{
				"revision": 3,
				"draft": legacy,
				"generation": {
					"id": "a" * 32,
					"status": "ready",
					"done": 2,
					"total": 2,
					"fingerprint": fingerprint,
				},
				"published_revision": None,
			}
		)
		path = self.root / "settings/settings.json"
		before = path.read_bytes()
		settings = api.get_settings()
		self.assertEqual(settings["draft"]["employee_voices"], {})
		self.assertTrue(settings["generation"]["can_publish"])
		self.assertEqual(path.read_bytes(), before)

	def test_personal_pitch_is_persisted_and_sent_to_engine(self):
		from hrms.utils import attendance_voice_engine

		personal = {**self.personal(), "pitch": 0.08}
		self.config["employee_voices"] = {"EMP-voice": personal}
		self.save()
		self.assertEqual(api.get_settings()["draft"]["employee_voices"]["EMP-voice"], personal)
		with patch.object(attendance_voice_engine, "render", side_effect=self.fake_render) as render:
			api.preview(json.dumps(self.config), "EMP-voice", "IN")
		self.assertEqual(
			render.call_args.args, ("voicevox", 29, "ワンさん、おはようございます。", 1.2, 0.3, 0.08)
		)

	def test_invalid_pitch_is_rejected_before_render(self):
		for value in (-0.16, 0.16, float("nan"), float("inf"), "bad"):
			self.config["employee_voices"] = {"EMP-voice": {**self.personal(), "pitch": value}}
			with (
				self.subTest(pitch=value),
				patch.object(service, "_render", side_effect=self.fake_render),
				self.assertRaises(frappe.ValidationError),
			):
				api.preview(json.dumps(self.config), "EMP-voice", "IN")
