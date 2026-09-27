import unittest
from unittest.mock import patch

import frappe

from hrms.api import checkin_presence
from hrms.api.checkin_presence import evaluate_presence

OFFICE = frappe._dict(latitude=35.6812, longitude=139.7671, checkin_radius=200)


class TestCheckinPresence(unittest.TestCase):
	def _evaluate(self, *, office=False, geofence=OFFICE, **kwargs):
		with (
			patch.object(checkin_presence, "is_office_network", return_value=office),
			patch.object(checkin_presence, "get_location_geofence", return_value=geofence),
		):
			return evaluate_presence("door", "198.51.100.1", **kwargs)

	def test_office_network_is_enough_without_location(self):
		result = self._evaluate(office=True)
		self.assertTrue(result.ok)
		self.assertEqual(result.evidence, "office_network")

	def test_missing_location_asks_for_it(self):
		self.assertEqual(self._evaluate().status, "need_location")

	def test_invalid_coordinates_are_treated_as_missing(self):
		for lat, lng in (("abc", 139.7), (35.6, None), (float("nan"), 139.7), (91, 139.7), (0, 0)):
			with self.subTest(lat=lat, lng=lng):
				self.assertEqual(
					self._evaluate(latitude=lat, longitude=lng, accuracy=10).status, "need_location"
				)

	def test_inside_radius_with_good_accuracy(self):
		result = self._evaluate(latitude=35.6813, longitude=139.7672, accuracy=20)
		self.assertTrue(result.ok)
		self.assertEqual(result.evidence, "gps")

	def test_missing_accuracy_relies_on_distance(self):
		self.assertTrue(self._evaluate(latitude="35.6813", longitude="139.7672").ok)

	def test_far_away_is_unconfirmed(self):
		result = self._evaluate(latitude=35.70, longitude=139.80, accuracy=10)
		self.assertEqual((result.status, result.reason), ("presence_unconfirmed", "too_far"))

	def test_poor_accuracy_is_unconfirmed(self):
		result = self._evaluate(latitude=35.6813, longitude=139.7672, accuracy=500)
		self.assertEqual(result.reason, "low_accuracy")

	def test_location_without_geofence_is_unconfirmed(self):
		result = self._evaluate(geofence=None, latitude=35.6813, longitude=139.7672)
		self.assertEqual(result.reason, "no_geofence")
