# Copyright (c) 2025, 株式会社UO and Contributors
# See license.txt

import hashlib
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

# 失败时测试运行器会把各层的局部变量也打出来：密钥值不能放进局部变量，
# 断言也不能带出实际值，所以这里只拿「是不是 64 位十六进制」和「摘要」。


def _password(name: str, fieldname: str) -> str | None:
	doc = frappe.get_doc("QR Checkin Location", name)
	return doc.get_password(fieldname, raise_exception=False)


def _password_is_hex64(name: str, fieldname: str) -> bool:
	return bool(HEX64.match(_password(name, fieldname) or ""))


def _password_digest(name: str, fieldname: str) -> str | None:
	"""密码字段的 SHA-256 摘要（没有值时返回 None），不暴露原值。"""
	value = _password(name, fieldname)
	return hashlib.sha256(value.encode()).hexdigest() if value else None


def _delete_location(name: str):
	if frappe.db.exists("QR Checkin Location", name):
		frappe.delete_doc("QR Checkin Location", name, force=True, ignore_permissions=True)


class TestQRCheckinLocationBleKey(HRMSTestSuite):
	"""蓝牙密钥：新建时生成、保存不变、补丁补齐。"""

	def make_location(self, name: str):
		_delete_location(name)
		doc = frappe.get_doc(
			{
				"doctype": "QR Checkin Location",
				"location_name": name,
				"secret": "test_secret_key_123456",
				"enabled": 1,
				"qr_refresh_interval": 30,
			}
		)
		doc.insert()
		self.addCleanup(_delete_location, name)
		return doc

	def clear_ble_key(self, name: str, column_value: str | None):
		"""模拟密钥丢失：库里的列（Password 字段存的是星号）和 __Auth 表里的真值都清掉。"""
		frappe.db.set_value("QR Checkin Location", name, "ble_key", column_value)
		frappe.db.delete("__Auth", {"doctype": "QR Checkin Location", "name": name, "fieldname": "ble_key"})
		self.assertTrue(_password(name, "ble_key") is None, "ble_key should be gone before the patch runs")

	def test_new_location_gets_ble_key(self):
		doc = self.make_location("test-ble-new")
		self.assertTrue(_password_is_hex64(doc.name, "ble_key"), "ble_key is not 64 lowercase hex")
		key_digest = _password_digest(doc.name, "ble_key")
		self.assertTrue(
			key_digest != _password_digest(doc.name, "display_key"), "ble_key equals display_key"
		)
		self.assertTrue(key_digest != _password_digest(doc.name, "secret"), "ble_key equals secret")

	def test_existing_ble_key_is_kept(self):
		doc = self.make_location("test-ble-kept")
		digest_before = _password_digest(doc.name, "ble_key")
		doc = frappe.get_doc("QR Checkin Location", doc.name)
		doc.description = "changed"
		doc.save()
		self.assertTrue(
			digest_before == _password_digest(doc.name, "ble_key"), "ble_key changed after saving again"
		)

	def test_patch_fills_missing_keys(self):
		from hrms.patches.v16_0 import generate_qr_ble_keys

		empty = self.make_location("test-ble-empty")
		kept = self.make_location("test-ble-patch-kept")
		digest_kept = _password_digest(kept.name, "ble_key")
		self.clear_ble_key(empty.name, None)

		generate_qr_ble_keys.execute()

		self.assertTrue(_password_is_hex64(empty.name, "ble_key"), "patch did not fill the missing ble_key")
		self.assertTrue(
			digest_kept == _password_digest(kept.name, "ble_key"), "patch changed an existing ble_key"
		)
