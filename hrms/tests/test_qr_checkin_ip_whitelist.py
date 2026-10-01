import unittest
from unittest.mock import patch

import frappe

from hrms.api import qr_attendance


class TestQRCheckinIPWhitelist(unittest.TestCase):
	def _settings(self, enabled, allowed):
		return frappe._dict(qr_checkin_ip_restriction=enabled, qr_checkin_allowed_ips=allowed)

	def test_blocks_request_outside_whitelist(self):
		with (
			patch.object(
				qr_attendance.frappe, "get_cached_doc", return_value=self._settings(1, "203.0.113.10")
			),
			patch.object(qr_attendance, "get_client_ip", return_value="198.51.100.1", create=True),
		):
			with self.assertRaises(frappe.exceptions.SecurityException):
				qr_attendance.validate_ip_whitelist()

	def test_allows_request_inside_ipv6_prefix(self):
		with (
			patch.object(
				qr_attendance.frappe, "get_cached_doc", return_value=self._settings(1, "2001:db8:1:2::/64")
			),
			patch.object(qr_attendance, "get_client_ip", return_value="2001:db8:1:2::99", create=True),
		):
			qr_attendance.validate_ip_whitelist()

	def test_disabled_or_empty_list_allows_everyone(self):
		for settings in (
			self._settings(0, "203.0.113.10"),
			self._settings(1, ""),
			self._settings(1, "# only comment"),
		):
			with (
				self.subTest(settings=settings),
				patch.object(qr_attendance.frappe, "get_cached_doc", return_value=settings),
				patch.object(qr_attendance, "get_client_ip", return_value="198.51.100.1", create=True),
			):
				qr_attendance.validate_ip_whitelist()

	def test_settings_read_failure_does_not_block_checkin(self):
		with (
			patch.object(qr_attendance.frappe, "get_cached_doc", side_effect=RuntimeError("boom")),
			patch.object(qr_attendance.frappe, "log_error"),
		):
			qr_attendance.validate_ip_whitelist()


class TestOfficeNetworkSettingValidation(unittest.TestCase):
	def test_rejects_unrecognised_lines(self):
		from hrms.hr.doctype.hr_settings.hr_settings import validate_office_networks

		with self.assertRaises(frappe.ValidationError):
			validate_office_networks("203.0.113.10\nnot-a-network")
		validate_office_networks("203.0.113.10\n2001:db8::/64\n# note")
