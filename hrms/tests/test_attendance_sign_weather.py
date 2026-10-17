import copy
import unittest
import uuid
from unittest.mock import patch

import frappe

from hrms.utils import attendance_sign_weather as weather


class TestAttendanceSignWeather(unittest.TestCase):
	def setUp(self):
		self.prefix = "test-sign-weather-" + uuid.uuid4().hex
		self.patches = [
			patch.object(weather, "_cache_key", side_effect=lambda lang, day: f"{self.prefix}:{lang}:{day}"),
			patch.object(weather.time, "time", return_value=1000),
			patch.object(weather, "nowdate", return_value="2026-10-17"),
		]
		for p in self.patches:
			p.start()
		self.data = {
			"temp_c": 0,
			"maxtemp_c": 8.5,
			"mintemp_c": -2.3,
			"condition": {"text": "晴れ", "icon": "https://cdn.weatherapi.com/weather/64x64/day/113.png"},
		}

	def tearDown(self):
		for lang in ("ja", "zh", "en"):
			for day in ("2026-10-17", "2026-10-18"):
				key = f"{self.prefix}:{lang}:{day}"
				frappe.cache.delete_value(key)
				frappe.cache.delete_value(key + ":last-good")
		for p in reversed(self.patches):
			p.stop()

	def test_zero_negative_temperatures_and_success_cache(self):
		with patch.object(weather, "_source", return_value=self.data) as source:
			first = weather.get_snapshot("ja")
			second = weather.get_snapshot("ja")
		self.assertEqual(
			first["weather"],
			{
				"temp_c": 0,
				"maxtemp_c": 8.5,
				"mintemp_c": -2.3,
				"condition_text": "晴れ",
				"icon_key": "clear",
				"is_day": True,
			},
		)
		self.assertEqual((first["status"], first["fetched_at"], first["refresh_after"]), ("ok", 1000, 600))
		self.assertEqual(first, second)
		source.assert_called_once_with("ja")

	def test_cache_language_and_date_are_isolated(self):
		with patch.object(weather, "_source", return_value=self.data) as source:
			weather.get_snapshot("ja")
			weather.get_snapshot("zh")
			with patch.object(weather, "nowdate", return_value="2026-10-18"):
				weather.get_snapshot("ja")
		self.assertEqual(source.call_count, 3)

	def test_cached_refresh_hint_counts_down(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot("ja")
		with (
			patch.object(weather.time, "time", return_value=1599),
			patch.object(weather, "_source") as source,
		):
			self.assertEqual(weather.get_snapshot("ja")["refresh_after"], 1)
			source.assert_not_called()

	def test_source_failure_returns_stale_and_backs_off(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot("ja")
		with (
			patch.object(weather.time, "time", return_value=1601),
			patch.object(weather, "_source", return_value=None) as source,
		):
			first = weather.get_snapshot("ja")
			second = weather.get_snapshot("ja")
		self.assertEqual((first["status"], first["fetched_at"], first["refresh_after"]), ("stale", 1000, 60))
		self.assertEqual(first["weather"]["temp_c"], 0)
		self.assertEqual(first, second)
		source.assert_called_once()

	def test_no_history_or_old_history_is_unavailable(self):
		with patch.object(weather, "_source", return_value=None):
			cold = weather.get_snapshot("ja")
		self.assertEqual((cold["status"], cold["weather"], cold["fetched_at"]), ("unavailable", None, None))
		with (
			patch.object(weather.time, "time", return_value=1061),
			patch.object(weather, "_source", return_value=self.data),
		):
			weather.get_snapshot("ja")
		with (
			patch.object(weather.time, "time", return_value=4662),
			patch.object(weather, "_source", return_value=None),
		):
			old = weather.get_snapshot("ja")
		self.assertEqual(old["status"], "unavailable")
		self.assertIsNone(old["weather"])

	def test_yesterday_is_not_reused_as_today(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot("ja")
		with (
			patch.object(weather, "nowdate", return_value="2026-10-18"),
			patch.object(weather, "_source", return_value=None),
		):
			result = weather.get_snapshot("ja")
		self.assertEqual((result["status"], result["date"]), ("unavailable", "2026-10-18"))

	def test_stale_history_expires_even_during_retry_backoff(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot("ja")
		with (
			patch.object(weather.time, "time", return_value=4599),
			patch.object(weather, "_source", return_value=None),
		):
			self.assertEqual(weather.get_snapshot("ja")["status"], "stale")
		with (
			patch.object(weather.time, "time", return_value=4601),
			patch.object(weather, "_source") as source,
		):
			result = weather.get_snapshot("ja")
			self.assertEqual(result["status"], "unavailable")
			self.assertIsNone(result["weather"])
			source.assert_not_called()

	def test_bad_source_does_not_become_fake_zero_temperature(self):
		for data in (
			None,
			{},
			{"temp_c": None},
			{**self.data, "temp_c": float("nan")},
			{**self.data, "temp_c": float("inf")},
			{**self.data, "temp_c": False},
		):
			self.assertIsNone(weather._normalize(data))

	def test_icon_categories_day_night_and_unknown(self):
		for icon, expected in [
			(113, "clear"),
			(116, "partly_cloudy"),
			(122, "cloudy"),
			(143, "fog"),
			(176, "rain"),
			(338, "snow"),
			(350, "sleet"),
			(389, "thunder"),
			(999, "unknown"),
		]:
			data = copy.deepcopy(self.data)
			data["condition"]["icon"] = f"https://cdn.weatherapi.com/weather/64x64/night/{icon}.png"
			result = weather._normalize(data)
			self.assertEqual((result["icon_key"], result["is_day"]), (expected, False))
		data = copy.deepcopy(self.data)
		data["condition"]["icon"] = "not-a-weather-image"
		result = weather._normalize(data)
		self.assertEqual(result["icon_key"], "unknown")
		self.assertIsNone(result["is_day"])

	def test_optional_forecast_is_null_when_not_available(self):
		data = copy.deepcopy(self.data)
		data.pop("maxtemp_c")
		data["mintemp_c"] = float("nan")
		result = weather._normalize(data)
		self.assertIsNone(result["maxtemp_c"])
		self.assertIsNone(result["mintemp_c"])

	def test_provider_language_context_is_restored(self):
		previous = frappe.local.lang
		try:
			frappe.local.lang = "en"

			def source():
				self.assertEqual(frappe.local.lang, "zh")
				return self.data

			with patch("hrms.api.get_weather_data", side_effect=source):
				self.assertEqual(weather._source("zh"), self.data)
			self.assertEqual(frappe.local.lang, "en")
			with (
				patch("hrms.api.get_weather_data", side_effect=RuntimeError("private-provider-url")),
				patch.object(frappe, "log_error"),
			):
				self.assertIsNone(weather._source("zh"))
			self.assertEqual(frappe.local.lang, "en")
		finally:
			frappe.local.lang = previous

	def test_unsupported_language_is_rejected_before_source(self):
		with patch.object(weather, "_source") as source:
			with self.assertRaises(frappe.ValidationError):
				weather.get_snapshot("xx")
			source.assert_not_called()
