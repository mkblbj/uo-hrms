from webauthn.helpers import bytes_to_base64url

import frappe

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.tests.utils import HRMSTestSuite
from hrms.tests.webauthn_soft_authenticator import SoftAuthenticator

MIGRATION_USER = "passkey-migration@example.com"


class TestPasskeyMigration(HRMSTestSuite):
	def setUp(self):
		frappe.set_user("Administrator")
		self.employee = make_employee(MIGRATION_USER, company="_Test Company")
		frappe.db.delete("Passkey Credential", {"user": MIGRATION_USER})

	def test_extracts_public_key_from_stored_attestation(self):
		from hrms.patches.v16_0.migrate_passkey_public_keys import execute

		authenticator = SoftAuthenticator("localhost", "http://localhost:29830")
		registration = authenticator.register(bytes_to_base64url(b"c" * 32))
		good = frappe.get_doc(
			{
				"doctype": "Passkey Credential",
				"user": MIGRATION_USER,
				"employee": self.employee,
				"credential_id": authenticator.credential_id_b64,
				"public_key": registration["response"]["attestationObject"],
			}
		).insert(ignore_permissions=True)
		broken = frappe.get_doc(
			{
				"doctype": "Passkey Credential",
				"user": MIGRATION_USER,
				"employee": self.employee,
				"credential_id": "broken-credential",
				"public_key": "not-an-attestation",
			}
		).insert(ignore_permissions=True)

		execute()

		self.assertEqual(
			frappe.db.get_value("Passkey Credential", good.name, "credential_public_key"),
			bytes_to_base64url(authenticator.cose_public_key()),
		)
		self.assertFalse(frappe.db.get_value("Passkey Credential", broken.name, "credential_public_key"))
