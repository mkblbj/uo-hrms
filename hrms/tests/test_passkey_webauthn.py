import unittest
from unittest.mock import patch

from webauthn.helpers import bytes_to_base64url

import frappe

from hrms.api import passkey_webauthn as pw
from hrms.tests.webauthn_soft_authenticator import SoftAuthenticator

RP_ID = "localhost"
ORIGIN = "http://localhost:29830"


class TestPasskeyWebAuthn(unittest.TestCase):
	def setUp(self):
		self.conf = patch.dict(frappe.local.conf, {"passkey_rp_id": RP_ID, "passkey_origins": [ORIGIN]})
		self.conf.start()
		self.authenticator = SoftAuthenticator(RP_ID, ORIGIN, b"user@example.com")

	def tearDown(self):
		self.conf.stop()

	def _register(self):
		options = pw.build_registration_options(
			user="user@example.com", display_name="User", exclude_credential_ids=[], data={"user": "u"}
		)
		self.assertEqual(options["rp"]["id"], RP_ID)
		self.assertEqual(options["authenticatorSelection"]["userVerification"], "required")
		response = self.authenticator.register(options["challenge"])
		challenge = pw.extract_client_challenge(response)
		self.assertEqual(pw.pop_challenge(pw.PURPOSE_REGISTER, challenge), {"user": "u"})
		return pw.verify_registration(response, expected_challenge_b64=challenge), response

	def test_defaults_match_production(self):
		with patch.dict(frappe.local.conf, {"passkey_rp_id": None, "passkey_origins": None}):
			self.assertEqual(pw.get_rp_id(), "erphr.toiroworld.com")
			self.assertEqual(pw.get_expected_origins(), ["https://erphr.toiroworld.com"])

	def test_register_then_authenticate(self):
		verified, response = self._register()
		self.assertEqual(
			pw.extract_public_key_from_attestation(response["response"]["attestationObject"]),
			verified.credential_public_key,
		)
		options = pw.build_authentication_options(
			allow_credential_ids=[self.authenticator.credential_id_b64], data={"user": "u"}
		)
		self.assertEqual(options["allowCredentials"][0]["id"], self.authenticator.credential_id_b64)
		assertion = self.authenticator.authenticate(options["challenge"])
		result = pw.verify_assertion(
			assertion,
			expected_challenge_b64=options["challenge"],
			public_key_b64=bytes_to_base64url(verified.credential_public_key),
			current_sign_count=0,
		)
		self.assertTrue(result.user_verified)

	def test_rejects_forged_or_unverified_assertions(self):
		verified, _ = self._register()
		public_key = bytes_to_base64url(verified.credential_public_key)
		for kwargs in (
			{"tamper_signature": True},
			{"user_verified": False},
			{"origin": "https://evil.example"},
		):
			with self.subTest(kwargs=kwargs):
				options = pw.build_authentication_options(allow_credential_ids=[], data={})
				assertion = self.authenticator.authenticate(options["challenge"], **kwargs)
				with self.assertRaises(pw.PasskeyVerificationError):
					pw.verify_assertion(
						assertion,
						expected_challenge_b64=options["challenge"],
						public_key_b64=public_key,
						current_sign_count=0,
					)

	def test_rejects_registration_without_user_verification(self):
		options = pw.build_registration_options(
			user="user@example.com", display_name="User", exclude_credential_ids=[], data={}
		)
		response = self.authenticator.register(options["challenge"], user_verified=False)
		with self.assertRaises(pw.PasskeyVerificationError):
			pw.verify_registration(response, expected_challenge_b64=options["challenge"])

	def test_pop_challenge_is_single_use(self):
		challenge_b64 = pw.store_challenge(pw.PURPOSE_CHECKIN, b"x" * 32, {"k": 1}, 60)
		self.assertEqual(pw.pop_challenge(pw.PURPOSE_CHECKIN, challenge_b64), {"k": 1})
		self.assertIsNone(pw.pop_challenge(pw.PURPOSE_CHECKIN, challenge_b64))
		self.assertIsNone(pw.pop_challenge(pw.PURPOSE_REGISTER, challenge_b64))
		self.assertIsNone(pw.pop_challenge(pw.PURPOSE_CHECKIN, ""))

	def test_exclude_credentials_are_listed(self):
		options = pw.build_registration_options(
			user="user@example.com",
			display_name="User",
			exclude_credential_ids=[self.authenticator.credential_id_b64],
			data={},
		)
		self.assertEqual(options["excludeCredentials"][0]["id"], self.authenticator.credential_id_b64)

	def test_accepts_plain_text_user_handle_from_legacy_nfc_page(self):
		# 门口 NFC 页用的 SimpleWebAuthn 9 把 userHandle 当 UTF-8 文本返回（旧注册的 userHandle 是邮箱）
		verified, _ = self._register()
		options = pw.build_authentication_options(allow_credential_ids=[], data={})
		assertion = self.authenticator.authenticate(options["challenge"])
		# 这个邮箱去掉非 base64 字符后剩 21 个，按 base64url 解码必然失败
		assertion["response"]["userHandle"] = "e2e-passkey@example.com"
		result = pw.verify_assertion(
			assertion,
			expected_challenge_b64=options["challenge"],
			public_key_b64=bytes_to_base64url(verified.credential_public_key),
			current_sign_count=0,
		)
		self.assertTrue(result.user_verified)
		self.assertEqual(assertion["response"]["userHandle"], "e2e-passkey@example.com")
