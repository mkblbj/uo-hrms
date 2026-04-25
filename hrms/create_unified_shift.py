"""Create Unified Shift Type"""

import frappe
from frappe.utils import today

def create_unified_shift():
    """Create the unified shift type with flexible working hours settings"""
    
    shift_name = "统一班次"
    
    # Check if shift already exists
    if frappe.db.exists("Shift Type", shift_name):
        print(f"Shift Type '{shift_name}' already exists. Updating settings...")
        shift = frappe.get_doc("Shift Type", shift_name)
    else:
        print(f"Creating Shift Type '{shift_name}'...")
        shift = frappe.new_doc("Shift Type")
        shift.name = shift_name
    
    # Basic settings - Use wide time range to cover most working scenarios
    # 06:00 - 22:00 covers typical flexible working hours
    shift.start_time = "06:00:00"
    shift.end_time = "22:00:00"
    shift.color = "Green"
    
    # Auto attendance settings
    shift.enable_auto_attendance = 1
    shift.determine_check_in_and_check_out = "Alternating entries as IN and OUT during the same shift"
    shift.working_hours_calculation_based_on = "First Check-in and Last Check-out"
    # Allow check-in 2 hours before (from 04:00) and check-out 2 hours after (until 00:00)
    shift.begin_check_in_before_shift_start_time = 120   # 2 hours before 06:00 = 04:00
    shift.allow_check_out_after_shift_end_time = 120     # 2 hours after 22:00 = 00:00
    shift.process_attendance_after = "2024-01-01"
    shift.auto_update_last_sync = 1
    
    # Flexible working hours settings
    shift.enable_time_rounding = 1
    shift.rounding_precision = "15"
    shift.enable_lunch_deduction = 1
    shift.lunch_start = "12:00:00"
    shift.lunch_end = "13:00:00"
    
    # Save
    shift.flags.ignore_permissions = True
    shift.save()
    
    frappe.db.commit()
    
    print(f"\n✅ Shift Type '{shift_name}' created/updated successfully!")
    print(f"\nSettings:")
    print(f"  - Start Time: {shift.start_time}")
    print(f"  - End Time: {shift.end_time}")
    print(f"  - Enable Auto Attendance: {shift.enable_auto_attendance}")
    print(f"  - Time Rounding: {shift.enable_time_rounding} (Precision: {shift.rounding_precision} min)")
    print(f"  - Lunch Deduction: {shift.enable_lunch_deduction} ({shift.lunch_start} - {shift.lunch_end})")
    
    return shift.name

