# Copyright (c) 2025, 株式会社UO and Contributors
# See license.txt

import re
import unittest

import frappe

from hrms.tests.utils import HRMSTestSuite


class TestQRCheckinLocation(unittest.TestCase):
	def test_create_location(self):
		"""测试创建打卡地点"""
		if frappe.db.exists("QR Checkin Location", "test-location"):
			frappe.delete_doc("QR Checkin Location", "test-location")

		doc = frappe.get_doc(
			{
				"doctype": "QR Checkin Location",
				"location_name": "test-location",
				"description": "测试地点",
				"secret": "test_secret_key_123456",
				"enabled": 1,
				"qr_refresh_interval": 30,
			}
		)
		doc.insert()

		self.assertEqual(doc.location_name, "test-location")
		self.assertTrue(doc.enabled)

		# 清理
		doc.delete()


HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _make_location(name: str, **extra):
	doc = frappe.get_doc(
		{
			"doctype": "QR Checkin Location",
			"location_name": name,
			"secret": "test_secret_key_123456",
			"enabled": 1,
			"qr_refresh_interval": 30,
			**extra,
		}
	)
	doc.insert()
	return doc


class TestQRCheckinLocationBleKey(HRMSTestSuite):
	"""蓝牙密钥：新建时生成、保存不变、补丁补齐。"""

	def test_new_location_gets_ble_key(self):
		doc = _make_location("test-ble-new")
		key = doc.get_password("ble_key")
		self.assertRegex(key, HEX64)
		self.assertNotEqual(key, doc.get_password("display_key"))
		self.assertNotEqual(key, doc.get_password("secret"))

	def test_existing_ble_key_is_kept(self):
		doc = _make_location("test-ble-kept")
		before = doc.get_password("ble_key")
		doc = frappe.get_doc("QR Checkin Location", "test-ble-kept")
		doc.description = "changed"
		doc.save()
		after = frappe.get_doc("QR Checkin Location", "test-ble-kept").get_password("ble_key")
		self.assertEqual(after, before)

	def test_patch_fills_missing_keys(self):
		from hrms.patches.v16_0 import generate_qr_ble_keys

		empty = _make_location("test-ble-empty")
		kept = _make_location("test-ble-patch-kept")
		kept_key = kept.get_password("ble_key")
		# Password 字段：库里存的是星号，真值在 __Auth 表，两处都要清
		frappe.db.set_value("QR Checkin Location", empty.name, "ble_key", None)
		frappe.db.delete(
			"__Auth", {"doctype": "QR Checkin Location", "name": empty.name, "fieldname": "ble_key"}
		)
		self.assertFalse(
			frappe.get_doc("QR Checkin Location", empty.name).get_password("ble_key", raise_exception=False)
		)

		generate_qr_ble_keys.execute()

		filled = frappe.get_doc("QR Checkin Location", empty.name).get_password("ble_key")
		self.assertRegex(filled, HEX64)
		self.assertEqual(frappe.get_doc("QR Checkin Location", kept.name).get_password("ble_key"), kept_key)
