"""签到牌蓝牙码的计算与核对（纯计算，不需要数据库）。"""

import unittest
from unittest.mock import patch

from hrms.utils import attendance_beacon
from hrms.utils.attendance_beacon import (
	beacon_code,
	beacon_slot,
	beacon_slot_offset,
	verify_beacon,
)

# 公开的测试向量密钥，不是任何真实密钥
TEST_KEY = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
LOCATION = "uo-2f-door"
NOW = 1792206020
SLOT = 179220602
CODE = "2b99c0d8"


def _with_key(key):
	return patch.object(attendance_beacon, "_location_ble_key", return_value=key)


class TestAttendanceBeacon(unittest.TestCase):
	def test_vectors(self):
		self.assertEqual(beacon_code(TEST_KEY, LOCATION, SLOT), CODE)
		self.assertEqual(beacon_code(TEST_KEY, LOCATION, 0), "4a2e3160")

	def test_slot(self):
		self.assertEqual(beacon_slot(1792206020), 179220602)
		self.assertEqual(beacon_slot(1792206030), 179220603)

	def test_slot_uses_now_when_missing(self):
		with patch.object(attendance_beacon, "_now", return_value=1792206020.5):
			self.assertEqual(beacon_slot(), 179220602)

	def test_verify_accepts_window(self):
		with _with_key(TEST_KEY):
			for slot in range(179220599, 179220604):
				with self.subTest(slot=slot):
					code = beacon_code(TEST_KEY, LOCATION, slot)
					self.assertTrue(verify_beacon(LOCATION, slot, code, now=NOW))
			for slot in (179220598, 179220604):
				with self.subTest(slot=slot):
					code = beacon_code(TEST_KEY, LOCATION, slot)
					self.assertFalse(verify_beacon(LOCATION, slot, code, now=NOW))

	def test_verify_uses_now_when_missing(self):
		with _with_key(TEST_KEY), patch.object(attendance_beacon, "_now", return_value=NOW):
			self.assertTrue(verify_beacon(LOCATION, SLOT, CODE))

	def test_verify_accepts_upper_case(self):
		with _with_key(TEST_KEY):
			self.assertTrue(verify_beacon(LOCATION, SLOT, "2B99C0D8", now=NOW))

	def test_verify_rejects_wrong_code(self):
		with _with_key(TEST_KEY):
			self.assertFalse(verify_beacon(LOCATION, SLOT, "2b99c0d9", now=NOW))

	def test_verify_rejects_malformed(self):
		with _with_key(TEST_KEY):
			for slot in (None, -1, "abc"):
				with self.subTest(slot=slot):
					self.assertFalse(verify_beacon(LOCATION, slot, CODE, now=NOW))
			for code in (None, "", "2b99c0d", "2b99c0dg"):
				with self.subTest(code=code):
					self.assertFalse(verify_beacon(LOCATION, SLOT, code, now=NOW))

	def test_verify_without_key(self):
		for key in (None, "", TEST_KEY[:-1]):
			with self.subTest(key=key), _with_key(key):
				self.assertFalse(verify_beacon(LOCATION, SLOT, CODE, now=NOW))

	def test_offset(self):
		self.assertEqual(beacon_slot_offset(179220600, now=NOW), -2)
		self.assertEqual(beacon_slot_offset(179220603, now=NOW), 1)
		for slot in (None, -1, "abc"):
			with self.subTest(slot=slot):
				self.assertIsNone(beacon_slot_offset(slot, now=NOW))
