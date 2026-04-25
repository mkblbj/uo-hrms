# -*- coding: utf-8 -*-
# Copyright (c) 2025, 株式会社UO and Contributors
# See license.txt

import unittest

import frappe


class TestQRCheckinLocation(unittest.TestCase):
	def test_create_location(self):
		"""测试创建打卡地点"""
		if frappe.db.exists("QR Checkin Location", "test-location"):
			frappe.delete_doc("QR Checkin Location", "test-location")
		
		doc = frappe.get_doc({
			"doctype": "QR Checkin Location",
			"location_name": "test-location",
			"description": "测试地点",
			"secret": "test_secret_key_123456",
			"enabled": 1,
			"qr_refresh_interval": 30
		})
		doc.insert()
		
		self.assertEqual(doc.location_name, "test-location")
		self.assertTrue(doc.enabled)
		
		# 清理
		doc.delete()

