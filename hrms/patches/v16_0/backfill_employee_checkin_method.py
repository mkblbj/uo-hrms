import frappe


def execute():
	frappe.db.sql(
		"""update `tabEmployee Checkin` set checkin_method = 'Attendance Correction'
		where ifnull(checkin_method, '') = ''
		and (device_id = 'Attendance Correction' or ifnull(attendance_correction_request, '') != '')"""
	)
	frappe.db.sql(
		"""update `tabEmployee Checkin` set checkin_method = 'NFC Passkey'
		where ifnull(checkin_method, '') = '' and device_id like 'NFC-Passkey:%%'"""
	)
	locations = frappe.get_all("QR Checkin Location", pluck="name")
	if locations:
		frappe.db.sql(
			"""update `tabEmployee Checkin` set checkin_method = 'QR'
			where ifnull(checkin_method, '') = '' and device_id in %(locations)s""",
			{"locations": tuple(locations)},
		)
