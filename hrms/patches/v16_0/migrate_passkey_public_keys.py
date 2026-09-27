from webauthn.helpers import bytes_to_base64url

import frappe

from hrms.api.passkey_webauthn import extract_public_key_from_attestation


def execute():
	"""旧版把 attestationObject 原样存在 public_key，这里解析出公钥，现有用户不用重新注册。"""
	rows = frappe.get_all(
		"Passkey Credential",
		filters={"credential_public_key": ("is", "not set")},
		fields=["name", "public_key"],
	)
	for row in rows:
		try:
			public_key = extract_public_key_from_attestation(row.public_key)
		except Exception:
			frappe.log_error(title="Passkey public key migration failed", message=row.name)
			continue
		frappe.db.set_value(
			"Passkey Credential",
			row.name,
			"credential_public_key",
			bytes_to_base64url(public_key),
			update_modified=False,
		)
