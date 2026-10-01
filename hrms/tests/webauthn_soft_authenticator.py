"""测试用的软件通行密钥：生成与浏览器 JSON 格式一致的注册和认证响应。"""

import hashlib
import json
import os
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from webauthn.helpers import bytes_to_base64url, encode_cbor

FLAG_UP = 0x01
FLAG_UV = 0x04
FLAG_BE = 0x08
FLAG_BS = 0x10
FLAG_AT = 0x40


class SoftAuthenticator:
	def __init__(self, rp_id: str, origin: str, user_handle: bytes = b"user"):
		self.rp_id = rp_id
		self.origin = origin
		self.user_handle = user_handle
		self.private_key = ec.generate_private_key(ec.SECP256R1())
		self.credential_id = os.urandom(16)
		self.sign_count = 0

	@property
	def credential_id_b64(self) -> str:
		return bytes_to_base64url(self.credential_id)

	def cose_public_key(self) -> bytes:
		numbers = self.private_key.public_key().public_numbers()
		return encode_cbor(
			{
				1: 2,
				3: -7,
				-1: 1,
				-2: numbers.x.to_bytes(32, "big"),
				-3: numbers.y.to_bytes(32, "big"),
			}
		)

	def _auth_data(self, flags: int, attested: bool) -> bytes:
		data = (
			hashlib.sha256(self.rp_id.encode()).digest() + bytes([flags]) + struct.pack(">I", self.sign_count)
		)
		if attested:
			data += (
				bytes(16)
				+ struct.pack(">H", len(self.credential_id))
				+ self.credential_id
				+ self.cose_public_key()
			)
		return data

	def _client_data(self, ceremony: str, challenge_b64: str, origin: str | None) -> bytes:
		return json.dumps(
			{
				"type": ceremony,
				"challenge": challenge_b64,
				"origin": origin or self.origin,
				"crossOrigin": False,
			},
			separators=(",", ":"),
		).encode()

	def register(self, challenge_b64: str, *, user_verified: bool = True, origin: str | None = None) -> dict:
		flags = FLAG_UP | FLAG_AT | FLAG_BE | FLAG_BS | (FLAG_UV if user_verified else 0)
		attestation = encode_cbor(
			{"fmt": "none", "attStmt": {}, "authData": self._auth_data(flags, attested=True)}
		)
		client_data = self._client_data("webauthn.create", challenge_b64, origin)
		return {
			"id": self.credential_id_b64,
			"rawId": self.credential_id_b64,
			"type": "public-key",
			"response": {
				"clientDataJSON": bytes_to_base64url(client_data),
				"attestationObject": bytes_to_base64url(attestation),
				"transports": ["internal"],
			},
			"clientExtensionResults": {},
			"authenticatorAttachment": "platform",
		}

	def authenticate(
		self,
		challenge_b64: str,
		*,
		user_verified: bool = True,
		origin: str | None = None,
		increment: bool = False,
		tamper_signature: bool = False,
	) -> dict:
		if increment:
			self.sign_count += 1
		flags = FLAG_UP | FLAG_BE | FLAG_BS | (FLAG_UV if user_verified else 0)
		auth_data = self._auth_data(flags, attested=False)
		client_data = self._client_data("webauthn.get", challenge_b64, origin)
		signature = self.private_key.sign(
			auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256())
		)
		if tamper_signature:
			signature = signature[:-1] + bytes([signature[-1] ^ 0x01])
		return {
			"id": self.credential_id_b64,
			"rawId": self.credential_id_b64,
			"type": "public-key",
			"response": {
				"clientDataJSON": bytes_to_base64url(client_data),
				"authenticatorData": bytes_to_base64url(auth_data),
				"signature": bytes_to_base64url(signature),
				"userHandle": bytes_to_base64url(self.user_handle),
			},
			"clientExtensionResults": {},
			"authenticatorAttachment": "platform",
		}
