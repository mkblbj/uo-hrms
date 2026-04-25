# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, get_datetime
from datetime import datetime, timedelta


@frappe.whitelist()
def recalculate_attendance(employee, date):
    """
    Recalculate attendance for a specific employee and date.
    
    This will:
    1. Cancel any existing attendance for that date
    2. Clear attendance links from checkins
    3. Trigger auto-attendance calculation
    
    Args:
        employee: Employee ID
        date: Date string (YYYY-MM-DD)
    
    Returns:
        dict with status and message
    """
    date = getdate(date)
    
    # Step 1: Cancel existing attendance
    existing_attendance = frappe.db.get_all(
        "Attendance",
        filters={
            "employee": employee,
            "attendance_date": date,
            "docstatus": 1
        },
        pluck="name"
    )
    
    for att_name in existing_attendance:
        att_doc = frappe.get_doc("Attendance", att_name)
        att_doc.flags.ignore_permissions = True
        att_doc.cancel()
    
    # Step 2: Clear attendance links from checkins for that date
    start_datetime = datetime.combine(date, datetime.min.time())
    end_datetime = datetime.combine(date, datetime.max.time())
    
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET attendance = NULL
        WHERE employee = %s
          AND time >= %s
          AND time <= %s
    """, (employee, start_datetime, end_datetime))
    
    # Step 3: Get the shift for this employee
    shift_name = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": employee,
            "status": "Active",
            "start_date": ["<=", date],
            "docstatus": 1,
        },
        "shift_type",
        order_by="start_date desc"
    )
    
    if not shift_name:
        return {
            "status": "error",
            "message": _("No active shift assignment found for employee {0} on {1}").format(employee, date)
        }
    
    # Step 4: Get checkins for this date
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [start_datetime, end_datetime]],
            "skip_auto_attendance": 0
        },
        fields=["name", "employee", "log_type", "time", "shift", 
                "shift_start", "shift_end", "shift_actual_start", "shift_actual_end"],
        order_by="time"
    )
    
    if not checkins:
        return {
            "status": "warning",
            "message": _("No checkin records found for employee {0} on {1}").format(employee, date)
        }
    
    # Step 5: Calculate attendance using shift's get_attendance method
    shift_doc = frappe.get_doc("Shift Type", shift_name)
    
    # Update checkins with shift info if missing
    for checkin in checkins:
        if not checkin.shift:
            frappe.db.set_value("Employee Checkin", checkin.name, {
                "shift": shift_name,
                "shift_start": datetime.combine(date, get_datetime(f"{date} {shift_doc.start_time}").time()),
                "shift_end": datetime.combine(date, get_datetime(f"{date} {shift_doc.end_time}").time()),
            })
            checkin.shift = shift_name
            checkin.shift_start = datetime.combine(date, get_datetime(f"{date} {shift_doc.start_time}").time())
            checkin.shift_end = datetime.combine(date, get_datetime(f"{date} {shift_doc.end_time}").time())
    
    # Reload checkins with updated shift info
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [start_datetime, end_datetime]],
            "skip_auto_attendance": 0
        },
        fields=["name", "employee", "log_type", "time", "shift", 
                "shift_start", "shift_end", "shift_actual_start", "shift_actual_end"],
        order_by="time"
    )
    
    # Calculate attendance
    status, working_hours, late_entry, early_exit, in_time, out_time = shift_doc.get_attendance(checkins)
    
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
        None  # overtime_type
    )
    
    frappe.db.commit()
    
    if attendance:
        return {
            "status": "success",
            "message": _("Attendance recalculated successfully"),
            "attendance": attendance.name,
            "working_hours": working_hours,
            "attendance_status": status
        }
    else:
        return {
            "status": "error",
            "message": _("Failed to create attendance record")
        }


@frappe.whitelist()
def recalculate_attendance_for_date_range(employee, from_date, to_date):
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
        results.append({
            "date": str(current_date),
            **result
        })
        current_date += timedelta(days=1)
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    
    return {
        "status": "completed",
        "message": _("Recalculated {0} of {1} days").format(success_count, len(results)),
        "details": results
    }

