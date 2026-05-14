import unittest

import frappe

from hrms.api import calculate_pwa_attendance_totals


class TestPwaHomeDashboardStats(unittest.TestCase):
	def test_calculate_pwa_attendance_totals_weights_statuses(self):
		rows = [
			frappe._dict(status="Present", working_hours=8),
			frappe._dict(status="Work From Home", working_hours=7.5),
			frappe._dict(status="Half Day", working_hours=4),
			frappe._dict(status="Absent", working_hours=0),
			frappe._dict(status="On Leave", working_hours=0),
		]

		self.assertEqual(
			calculate_pwa_attendance_totals(rows),
			{
				"total_hours": 19.5,
				"total_present_days": 2.5,
			},
		)

	def test_calculate_pwa_attendance_totals_handles_missing_values(self):
		rows = [
			frappe._dict(status="Present", working_hours=None),
			frappe._dict(status="Half Day", working_hours=None),
			frappe._dict(status=None, working_hours=3),
		]

		self.assertEqual(
			calculate_pwa_attendance_totals(rows),
			{
				"total_hours": 3.0,
				"total_present_days": 1.5,
			},
		)


if __name__ == "__main__":
	unittest.main()
