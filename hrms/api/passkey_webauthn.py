"""通行密钥（WebAuthn）核对：py_webauthn 封装、RP 配置、一次性 challenge。

hrms.api 在导入时就会加载本模块，所以 webauthn 只在函数里导入：
即使环境里缺了这个包，也只影响面容/指纹打卡，不会让整个 hrms.api 失败。
"""

import base64
import hashlib
import json
import secrets

import frappe
from frappe import _

DEFAULT_RP_ID = "erphr.toiroworld.com"
DEFAULT_ORIGINS = ("https://erphr.toiroworld.com",)
DEFAULT_RP_NAME = "UO HR System"
REGISTRATION_TIMEOUT_SECONDS = 300
CHECKIN_TIMEOUT_SECONDS = 120

PURPOSE_REGISTER = "register"
PURPOSE_CHECKIN = "checkin"

INPUT_ERRORS = (ValueError, KeyError, TypeError)


class PasskeyVerificationError(frappe.ValidationError):
	pass


def b64url_encode(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(value: str) -> bytes:
	return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _verification_errors() -> tuple:
	from webauthn.helpers.exceptions import WebAuthnException

	return (WebAuthnException, *INPUT_ERRORS)


def get_rp_id() -> str:
	return frappe.conf.get("passkey_rp_id") or DEFAULT_RP_ID


def get_rp_name() -> str:
	return frappe.conf.get("passkey_rp_name") or DEFAULT_RP_NAME


def get_expected_origins() -> list[str]:
	origins = frappe.conf.get("passkey_origins") or DEFAULT_ORIGINS
	if isinstance(origins, str):
		origins = [origins]
	return list(origins)


def _challenge_key(purpose: str, challenge_b64: str) -> str:
	return f"passkey_challenge:{purpose}:{challenge_b64}"


def store_challenge(purpose: str, challenge: bytes, data: dict, ttl: int) -> str:
	challenge_b64 = b64url_encode(challenge)
	frappe.cache.set_value(_challenge_key(purpose, challenge_b64), json.dumps(data), expires_in_sec=ttl)
	return challenge_b64


def pop_challenge(purpose: str, challenge_b64: str) -> dict | None:
	if not challenge_b64:
		return None
	key = _challenge_key(purpose, challenge_b64)
	raw = frappe.cache.get_value(key, use_local_cache=False)
	if not raw:
		return None
	# DEL 返回删掉的个数：并发的第二个请求拿到 0，视为已用过
	if not frappe.cache.delete(frappe.cache.make_key(key)):
		return None
	return json.loads(raw)


def extract_client_challenge(credential: dict) -> str:
	try:
		client_data = json.loads(b64url_decode(credential["response"]["clientDataJSON"]))
	except INPUT_ERRORS:
		return ""
	if not isinstance(client_data, dict):
		return ""
	return client_data.get("challenge") or ""


def _descriptors(credential_ids: list[str]) -> list:
	from webauthn.helpers.structs import PublicKeyCredentialDescriptor

	return [PublicKeyCredentialDescriptor(id=b64url_decode(cid)) for cid in credential_ids]


def _user_handle(user: str) -> bytes:
	handle = user.encode()
	return handle if len(handle) <= 64 else hashlib.sha256(handle).digest()


def build_registration_options(
	*, user: str, display_name: str, exclude_credential_ids: list[str], data: dict
) -> dict:
	from webauthn import generate_registration_options
	from webauthn.helpers import options_to_json_dict
	from webauthn.helpers.structs import (
		AuthenticatorAttachment,
		AuthenticatorSelectionCriteria,
		ResidentKeyRequirement,
		UserVerificationRequirement,
	)

	challenge = secrets.token_bytes(32)
	options = generate_registration_options(
		rp_id=get_rp_id(),
		rp_name=get_rp_name(),
		user_id=_user_handle(user),
		user_name=user,
		user_display_name=display_name or user,
		challenge=challenge,
		timeout=REGISTRATION_TIMEOUT_SECONDS * 1000,
		authenticator_selection=AuthenticatorSelectionCriteria(
			authenticator_attachment=AuthenticatorAttachment.PLATFORM,
			resident_key=ResidentKeyRequirement.REQUIRED,
			user_verification=UserVerificationRequirement.REQUIRED,
		),
		exclude_credentials=_descriptors(exclude_credential_ids),
	)
	store_challenge(PURPOSE_REGISTER, challenge, data, REGISTRATION_TIMEOUT_SECONDS)
	return options_to_json_dict(options)


def verify_registration(credential: dict, *, expected_challenge_b64: str):
	from webauthn import verify_registration_response

	try:
		return verify_registration_response(
			credential=credential,
			expected_challenge=b64url_decode(expected_challenge_b64),
			expected_rp_id=get_rp_id(),
			expected_origin=get_expected_origins(),
			require_user_verification=True,
		)
	except _verification_errors() as error:
		raise PasskeyVerificationError(
			_("Face ID / fingerprint setup could not be verified. Please try again.")
		) from error


def build_authentication_options(
	*, allow_credential_ids: list[str], data: dict, purpose: str = PURPOSE_CHECKIN
) -> dict:
	from webauthn import generate_authentication_options
	from webauthn.helpers import options_to_json_dict
	from webauthn.helpers.structs import UserVerificationRequirement

	challenge = secrets.token_bytes(32)
	options = generate_authentication_options(
		rp_id=get_rp_id(),
		challenge=challenge,
		timeout=CHECKIN_TIMEOUT_SECONDS * 1000,
		allow_credentials=_descriptors(allow_credential_ids),
		user_verification=UserVerificationRequirement.REQUIRED,
	)
	store_challenge(purpose, challenge, data, CHECKIN_TIMEOUT_SECONDS)
	return options_to_json_dict(options)


def _without_user_handle(credential: dict) -> dict:
	"""核对签名用不到 userHandle（按凭证编号找人）；旧版前端库会把它当 UTF-8 文本
	（旧注册里是邮箱）返回，交给 py_webauthn 解析会失败，所以核对前去掉。"""
	response = credential.get("response")
	if not isinstance(response, dict) or "userHandle" not in response:
		return credential
	return {**credential, "response": {k: v for k, v in response.items() if k != "userHandle"}}


def verify_assertion(
	credential: dict, *, expected_challenge_b64: str, public_key_b64: str, current_sign_count: int
):
	from webauthn import verify_authentication_response

	try:
		return verify_authentication_response(
			credential=_without_user_handle(credential),
			expected_challenge=b64url_decode(expected_challenge_b64),
			expected_rp_id=get_rp_id(),
			expected_origin=get_expected_origins(),
			credential_public_key=b64url_decode(public_key_b64),
			credential_current_sign_count=int(current_sign_count or 0),
			require_user_verification=True,
		)
	except _verification_errors() as error:
		raise PasskeyVerificationError(
			_("Face ID / fingerprint could not be verified. Please try again.")
		) from error


def extract_public_key_from_attestation(attestation_object_b64: str) -> bytes:
	from webauthn.helpers import parse_attestation_object

	attestation = parse_attestation_object(b64url_decode(attestation_object_b64))
	attested = attestation.auth_data.attested_credential_data
	if not attested or not attested.credential_public_key:
		raise ValueError("attestation object has no credential public key")
	return attested.credential_public_key
