import unittest
from unittest.mock import patch

import frappe

from hrms.utils import client_network
from hrms.utils.client_network import (
	find_invalid_network_lines,
	get_client_ip,
	is_office_network,
	parse_network_list,
)

NETWORKS = """
# 公司
203.0.113.10
2001:db8:10:20::/64

198.51.100.0/24
"""


class TestClientNetwork(unittest.TestCase):
	def setUp(self):
		self._request = getattr(frappe.local, "request", None)
		self._request_ip = getattr(frappe.local, "request_ip", None)

	def tearDown(self):
		frappe.local.request = self._request
		frappe.local.request_ip = self._request_ip

	def _set_request(self, headers, request_ip):
		frappe.local.request = frappe._dict(headers=headers)
		frappe.local.request_ip = request_ip

	def test_prefers_cloudflare_connecting_ip_over_forwarded_for(self):
		self._set_request({"CF-Connecting-IP": "198.51.100.7"}, "203.0.113.10")
		self.assertEqual(get_client_ip(), "198.51.100.7")

	def test_invalid_cloudflare_header_falls_back_to_request_ip(self):
		self._set_request({"CF-Connecting-IP": "not-an-ip"}, "192.0.2.5")
		self.assertEqual(get_client_ip(), "192.0.2.5")

	def test_without_request_uses_request_ip(self):
		frappe.local.request = None
		frappe.local.request_ip = "192.0.2.9"
		self.assertEqual(get_client_ip(), "192.0.2.9")

	def test_parse_skips_comments_blank_and_invalid_lines(self):
		networks = parse_network_list(NETWORKS + "\nbogus\n")
		self.assertEqual(
			[str(n) for n in networks], ["203.0.113.10/32", "2001:db8:10:20::/64", "198.51.100.0/24"]
		)
		self.assertEqual(find_invalid_network_lines(NETWORKS + "\nbogus\n"), ["bogus"])

	def test_matches_exact_ipv4_cidr_and_ipv6_prefix(self):
		self.assertTrue(is_office_network("203.0.113.10", NETWORKS))
		self.assertTrue(is_office_network("198.51.100.200", NETWORKS))
		self.assertTrue(is_office_network("2001:db8:10:20:abcd::1", NETWORKS))
		self.assertFalse(is_office_network("2001:db8:10:21::1", NETWORKS))
		self.assertFalse(is_office_network("203.0.113.11", NETWORKS))

	def test_ipv4_mapped_ipv6_matches_ipv4_network(self):
		self.assertTrue(is_office_network("::ffff:203.0.113.10", NETWORKS))

	def test_empty_or_invalid_input_is_not_office(self):
		self.assertFalse(is_office_network(None, NETWORKS))
		self.assertFalse(is_office_network("garbage", NETWORKS))
		self.assertFalse(is_office_network("203.0.113.10", ""))

	def test_reads_hr_settings_when_text_not_given(self):
		with patch.object(client_network.frappe.db, "get_single_value", return_value="203.0.113.10") as getter:
			self.assertTrue(is_office_network("203.0.113.10"))
		getter.assert_called_once_with("HR Settings", "qr_checkin_allowed_ips")
