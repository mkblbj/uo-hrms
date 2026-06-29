import unittest
from unittest.mock import patch

import frappe

from hrms.api import qr_attendance


class TestQRAttendance(unittest.TestCase):
	def test_get_employees_at_work_includes_checked_out_employees_from_today(self):
		def fake_sql(sql, params, as_dict=False):
			if "ec.log_type = 'IN'" in sql:
				return []
			return [
				frappe._dict(
					employee="HR-EMP-00001",
					employee_name="李雪莉",
					log_type="OUT",
					time="2026-06-27 18:05:00",
					location="office-10F",
					department="Production",
					designation="Staff",
					image=None,
				)
			]

		with (
			patch("frappe.utils.today", return_value="2026-06-27"),
			patch.object(qr_attendance.frappe.db, "sql", side_effect=fake_sql),
		):
			result = qr_attendance.get_employees_at_work()

		self.assertEqual(result["count"], 1)
		self.assertEqual(result["employees"][0]["employee_name"], "李雪莉")
		self.assertEqual(result["employees"][0]["attendance_status"], "off_work")
		self.assertEqual(result["employees"][0]["attendance_status_label"], "退勤済")
		self.assertEqual(result["employees"][0]["last_log_type"], "OUT")
		self.assertEqual(result["employees"][0]["checkin_time"], "18:05:00")
		self.assertEqual(result["employees"][0]["last_checkin_time"], "18:05")
		self.assertEqual(result["employees"][0]["last_checkin_location"], "office-10F")


if __name__ == "__main__":
	unittest.main()
