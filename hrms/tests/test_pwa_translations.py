import unittest
from unittest.mock import patch

import frappe

from hrms.api import get_pwa_translations, normalize_pwa_language


class TestPwaTranslations(unittest.TestCase):
	def test_normalize_pwa_language_variants(self):
		self.assertEqual(normalize_pwa_language("zh-CN"), "zh")
		self.assertEqual(normalize_pwa_language("ja_JP"), "ja")
		self.assertEqual(normalize_pwa_language("en-US"), "en")
		self.assertEqual(normalize_pwa_language(""), "")

	@patch("hrms.api.get_all_translations", return_value={"Settings": "設定"})
	def test_get_pwa_translations_returns_requested_dictionary(self, mocked_get_all_translations):
		messages = get_pwa_translations("ja")

		self.assertIsInstance(messages, dict)
		self.assertEqual(messages.get("Settings"), "設定")
		mocked_get_all_translations.assert_called_once_with("ja")

	@patch("hrms.api.frappe.throw", side_effect=frappe.ValidationError)
	def test_get_pwa_translations_rejects_unsupported_language(self, mocked_throw):
		with self.assertRaises(frappe.ValidationError):
			get_pwa_translations("fr")

		mocked_throw.assert_called_once()


if __name__ == "__main__":
	unittest.main()
