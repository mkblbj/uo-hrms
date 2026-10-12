# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import get_timedelta, getdate


@frappe.whitelist()
def recalculate_attendance(
	employee: str, date: str, commit: bool = True, ignore_permissions: bool = False
) -> dict:
	"""
	Recalculate attendance for a specific employee and date.

	This will:
	1. Defer unfinished shifts until their check-out window closes
	2. Recover checkins skipped because attendance had already been submitted
	3. Cancel existing attendance and recalculate from the applicable checkins

	Args:
	    employee: Employee ID
	    date: Date string (YYYY-MM-DD)
	    commit: Commit attendance recalculation changes before returning.
	    ignore_permissions: Create recalculated Attendance as a system action.

	Returns:
	    dict with status and message
	"""
	date = getdate(date)

	# Resolve the shift before changing any existing attendance.
	shift_name = frappe.db.get_value(
		"Shift Assignment",
		{
			"employee": employee,
			"status": "Active",
			"start_date": ["<=", date],
			"docstatus": 1,
		},
		"shift_type",
		order_by="start_date desc",
	)

	if not shift_name:
		return {
			"status": "error",
			"message": _("No active shift assignment found for employee {0} on {1}").format(employee, date),
		}

	shift_doc = frappe.get_doc("Shift Type", shift_name)
	start_datetime, end_datetime = get_attendance_recalculation_window(shift_doc, date)

	restore_checkins_skipped_for_existing_attendance(employee, date, start_datetime, end_datetime)

	existing_attendance = frappe.db.get_all(
		"Attendance", filters={"employee": employee, "attendance_date": date, "docstatus": 1}, pluck="name"
	)
	for att_name in existing_attendance:
		att_doc = frappe.get_doc("Attendance", att_name)
		att_doc.flags.ignore_permissions = True
		att_doc.cancel()

	# Step 3: Clear attendance links from checkins in this shift window
	frappe.db.sql(
		"""
        UPDATE `tabEmployee Checkin`
        SET attendance = NULL
        WHERE employee = %s
          AND time >= %s
          AND time <= %s
    """,
		(employee, start_datetime, end_datetime),
	)

	if frappe.utils.now_datetime() <= end_datetime:
		if commit:
			frappe.db.commit()
		return {
			"status": "deferred",
			"message": _("Attendance will be calculated after the shift check-out window closes."),
		}

	# Step 4: Get checkins for this shift window
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [start_datetime, end_datetime]],
			"skip_auto_attendance": 0,
		},
		fields=[
			"name",
			"employee",
			"log_type",
			"time",
			"shift",
			"shift_start",
			"shift_end",
			"shift_actual_start",
			"shift_actual_end",
			"offshift",
		],
		order_by="time",
	)

	if not checkins:
		return {
			"status": "warning",
			"message": _("No checkin records found for employee {0} on {1}").format(employee, date),
		}

	# Update checkins with shift info if missing
	for checkin in checkins:
		if not checkin.shift or checkin.offshift:
			checkin_doc = frappe.get_doc("Employee Checkin", checkin.name)
			checkin_doc.fetch_shift()
			checkin_doc.flags.ignore_validate = True
			checkin_doc.save()

	# Reload checkins with updated shift info
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [start_datetime, end_datetime]],
			"skip_auto_attendance": 0,
		},
		fields=[
			"name",
			"employee",
			"log_type",
			"time",
			"shift",
			"shift_start",
			"shift_end",
			"shift_actual_start",
			"shift_actual_end",
			"offshift",
		],
		order_by="time",
	)

	checkins = [checkin for checkin in checkins if checkin.shift == shift_name and not checkin.offshift]

	if not checkins:
		return {
			"status": "warning",
			"message": _("No valid checkin records found for employee {0} on {1}").format(employee, date),
		}

	status, working_hours, late_entry, early_exit, in_time, out_time = shift_doc.get_attendance(
		checkins,
		shift_doc.working_hours_threshold_for_absent,
		shift_doc.working_hours_threshold_for_half_day,
	)

	# Step 6: Create new attendance
	from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log

	attendance = mark_attendance_and_link_log(
		checkins,
		status,
		date,
		working_hours,
		late_entry,
		early_exit,
		in_time,
		out_time,
		shift_name,
		None,  # overtime_type
		ignore_permissions=ignore_permissions,
	)

	if commit:
		frappe.db.commit()

	if attendance:
		return {
			"status": "success",
			"message": _("Attendance recalculated successfully"),
			"attendance": attendance.name,
			"working_hours": working_hours,
			"attendance_status": status,
		}
	else:
		return {"status": "error", "message": _("Failed to create attendance record")}


def restore_checkins_skipped_for_existing_attendance(employee, date, start_datetime, end_datetime):
	"""Recover automatic attendance conflicts without enabling manually skipped punches."""
	skipped_logs = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [start_datetime, end_datetime]],
			"skip_auto_attendance": 1,
		},
		pluck="name",
	)
	if not skipped_logs:
		return

	attendance_names = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": date, "docstatus": ["in", [1, 2]]},
		pluck="name",
	)
	comments = frappe.get_all(
		"Comment",
		filters={
			"reference_doctype": "Employee Checkin",
			"reference_name": ["in", skipped_logs],
			"comment_type": "Comment",
		},
		fields=["reference_name", "content"],
	)
	# handle_attendance_exception records the conflict as a bold prefix, a line
	# break, and a link to the existing Attendance, independently of its language.
	recovered_logs = {
		comment.reference_name
		for comment in comments
		if (comment.content or "").startswith("<strong>")
		and "<br>" in comment.content
		and any(f"/attendance/{name}" in comment.content for name in attendance_names)
	}
	if recovered_logs:
		frappe.db.set_value("Employee Checkin", {"name": ["in", recovered_logs]}, "skip_auto_attendance", 0)


def get_attendance_recalculation_window(shift_doc, date: str) -> tuple[datetime, datetime]:
	date = getdate(date)
	start_time = get_timedelta(shift_doc.start_time) or timedelta()
	end_time = get_timedelta(shift_doc.end_time) or timedelta()
	start_datetime = datetime.combine(date, datetime.min.time()) + start_time
	end_datetime = datetime.combine(date, datetime.min.time()) + end_time

	if start_time > end_time:
		end_datetime += timedelta(days=1)

	start_datetime -= timedelta(minutes=shift_doc.begin_check_in_before_shift_start_time or 0)
	end_datetime += timedelta(minutes=shift_doc.allow_check_out_after_shift_end_time or 0)
	return start_datetime, end_datetime


@frappe.whitelist()
def recalculate_attendance_for_date_range(employee: str, from_date: str, to_date: str) -> dict:
	"""
	Recalculate attendance for a date range.

	Args:
	    employee: Employee ID
	    from_date: Start date (YYYY-MM-DD)
	    to_date: End date (YYYY-MM-DD)

	Returns:
	    dict with results
	"""
	from_date = getdate(from_date)
	to_date = getdate(to_date)

	results = []
	current_date = from_date

	while current_date <= to_date:
		result = recalculate_attendance(employee, str(current_date))
		results.append({"date": str(current_date), **result})
		current_date += timedelta(days=1)

	success_count = sum(1 for r in results if r.get("status") == "success")

	return {
		"status": "completed",
		"message": _("Recalculated {0} of {1} days").format(success_count, len(results)),
		"details": results,
	}
