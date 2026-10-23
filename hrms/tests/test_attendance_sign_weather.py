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
			patch.object(weather, "_cache_key", side_effect=lambda day: f"{self.prefix}:ja:{day}"),
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
		for day in ("2026-10-17", "2026-10-18"):
			key = f"{self.prefix}:ja:{day}"
			frappe.cache.delete_value(key)
			frappe.cache.delete_value(key + ":last-good")
		for p in reversed(self.patches):
			p.stop()

	def test_zero_negative_temperatures_and_success_cache(self):
		with patch.object(weather, "_source", return_value=self.data) as source:
			first = weather.get_snapshot()
			second = weather.get_snapshot()
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
		source.assert_called_once_with()

	def test_cache_dates_are_isolated(self):
		with patch.object(weather, "_source", return_value=self.data) as source:
			weather.get_snapshot()
			with patch.object(weather, "nowdate", return_value="2026-10-18"):
				weather.get_snapshot()
		self.assertEqual(source.call_count, 2)

	def test_cached_refresh_hint_counts_down(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot()
		with (
			patch.object(weather.time, "time", return_value=1599),
			patch.object(weather, "_source") as source,
		):
			self.assertEqual(weather.get_snapshot()["refresh_after"], 1)
			source.assert_not_called()

	def test_source_failure_returns_stale_and_backs_off(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot()
		with (
			patch.object(weather.time, "time", return_value=1601),
			patch.object(weather, "_source", return_value=None) as source,
		):
			first = weather.get_snapshot()
			second = weather.get_snapshot()
		self.assertEqual((first["status"], first["fetched_at"], first["refresh_after"]), ("stale", 1000, 60))
		self.assertEqual(first["weather"]["temp_c"], 0)
		self.assertEqual(first, second)
		source.assert_called_once()

	def test_no_history_or_old_history_is_unavailable(self):
		with patch.object(weather, "_source", return_value=None):
			cold = weather.get_snapshot()
		self.assertEqual((cold["status"], cold["weather"], cold["fetched_at"]), ("unavailable", None, None))
		with (
			patch.object(weather.time, "time", return_value=1061),
			patch.object(weather, "_source", return_value=self.data),
		):
			weather.get_snapshot()
		with (
			patch.object(weather.time, "time", return_value=4662),
			patch.object(weather, "_source", return_value=None),
		):
			old = weather.get_snapshot()
		self.assertEqual(old["status"], "unavailable")
		self.assertIsNone(old["weather"])

	def test_yesterday_is_not_reused_as_today(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot()
		with (
			patch.object(weather, "nowdate", return_value="2026-10-18"),
			patch.object(weather, "_source", return_value=None),
		):
			result = weather.get_snapshot()
		self.assertEqual((result["status"], result["date"]), ("unavailable", "2026-10-18"))

	def test_stale_history_expires_even_during_retry_backoff(self):
		with patch.object(weather, "_source", return_value=self.data):
			weather.get_snapshot()
		with (
			patch.object(weather.time, "time", return_value=4599),
			patch.object(weather, "_source", return_value=None),
		):
			self.assertEqual(weather.get_snapshot()["status"], "stale")
		with (
			patch.object(weather.time, "time", return_value=4601),
			patch.object(weather, "_source") as source,
		):
			result = weather.get_snapshot()
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
			frappe.local.lang = "zh"

			def source():
				self.assertEqual(frappe.local.lang, "ja")
				return self.data

			with patch("hrms.api.get_weather_data", side_effect=source):
				self.assertEqual(weather._source(), self.data)
			self.assertEqual(frappe.local.lang, "zh")
			with (
				patch("hrms.api.get_weather_data", side_effect=RuntimeError("private-provider-url")),
				patch.object(frappe, "log_error"),
			):
				self.assertIsNone(weather._source())
			self.assertEqual(frappe.local.lang, "zh")
		finally:
			frappe.local.lang = previous

	def test_provider_request_is_https_and_failure_log_hides_url(self):
		# 天气源只给签到牌用：走 https；失败时日志只记异常类型，不带网址和密钥
		import requests

		import hrms.api

		import sys

		failure = requests.ConnectionError("HTTPConnectionPool: /v1/forecast.json?key=SECRET-IN-URL")
		raised_at_log_time = []
		with (
			patch("requests.get", side_effect=failure) as get,
			patch.object(
				frappe, "log_error", side_effect=lambda **kw: raised_at_log_time.append(sys.exc_info()[0])
			) as log_error,
		):
			self.assertIsNone(hrms.api.get_weather_data())
		self.assertTrue(get.call_args.args[0].startswith("https://api.weatherapi.com/"))
		logged = repr(log_error.call_args)
		self.assertNotIn("SECRET-IN-URL", logged)
		self.assertNotIn("key=", logged)
		self.assertEqual(log_error.call_args.kwargs["message"], "ConnectionError")
		# 记日志时已不在 except 里，错误上报拿不到带网址的异常
		self.assertEqual(raised_at_log_time, [None])

	def test_provider_http_error_logs_only_the_status(self):
		import requests

		import hrms.api

		response = requests.Response()
		response.status_code = 403
		failure = requests.HTTPError("403 Client Error for url: https://x/?key=SECRET-IN-URL", response=response)
		reply = patch("requests.get").start()
		self.addCleanup(patch.stopall)
		reply.return_value.raise_for_status.side_effect = failure
		with patch.object(frappe, "log_error") as log_error:
			self.assertIsNone(hrms.api.get_weather_data())
		self.assertEqual(log_error.call_args.kwargs["message"], "HTTPError (HTTP 403)")

	def test_provider_success_is_parsed(self):
		import hrms.api

		payload = {
			"current": {"temp_c": 18.5, "condition": {"text": "晴れ", "icon": "//cdn.weatherapi.com/weather/64x64/day/113.png"}},
			"forecast": {"forecastday": [{"day": {"maxtemp_c": 22.1, "mintemp_c": 12.4}}]},
		}
		with patch("requests.get") as get:
			get.return_value.json.return_value = payload
			result = hrms.api.get_weather_data()
		self.assertEqual(
			result,
			{
				"temp_c": 18.5,
				"condition": {"text": "晴れ", "icon": "https://cdn.weatherapi.com/weather/64x64/day/113.png"},
				"maxtemp_c": 22.1,
				"mintemp_c": 12.4,
			},
		)
		url = get.call_args.args[0]
		self.assertTrue(url.startswith("https://api.weatherapi.com/v1/forecast.json?"))
		self.assertTrue("&q=34.66497,135.1582&" in url and "&dt=" in url)
