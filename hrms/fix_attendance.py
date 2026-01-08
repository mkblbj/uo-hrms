# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def fix_employee_jan5_attendance(employee="50", date="2026-01-05"):
    """修复员工的跨天考勤问题"""
    
    # 1. 取消并删除该日期的所有考勤记录
    print(f"Step 1: 取消 {employee} 在 {date} 的考勤记录...")
    attendances = frappe.get_all(
        "Attendance",
        filters={"employee": employee, "attendance_date": date},
        pluck="name"
    )
    
    for att_name in attendances:
        att_doc = frappe.get_doc("Attendance", att_name)
        if att_doc.docstatus == 1:
            att_doc.flags.ignore_permissions = True
            att_doc.cancel()
            print(f"  已取消: {att_name}")
        frappe.delete_doc("Attendance", att_name, force=True)
        print(f"  已删除: {att_name}")
    
    # 2. 清除相关签到记录的 attendance 关联（包括次日凌晨的签退）
    print(f"\nStep 2: 清除签到记录的考勤关联...")
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin` 
        SET attendance = NULL
        WHERE employee = %s 
        AND shift_start >= %s 
        AND shift_start < %s
    """, (employee, f"{date} 00:00:00", f"{date} 23:59:59"))
    
    # 3. 修复签到记录的 shift_actual_end（确保都是 03:00）
    print(f"\nStep 3: 修复 shift_actual_end...")
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET shift_actual_end = DATE_ADD(DATE(shift_start), INTERVAL 27 HOUR)
        WHERE employee = %s
        AND shift_start >= %s
        AND shift_start < %s
        AND shift = '统一班次'
    """, (employee, f"{date} 00:00:00", f"{date} 23:59:59"))
    
    frappe.db.commit()
    
    # 4. 验证数据
    print(f"\nStep 4: 验证数据...")
    checkins = frappe.db.sql("""
        SELECT name, time, log_type, shift_start, shift_actual_end, attendance
        FROM `tabEmployee Checkin`
        WHERE employee = %s
        AND time >= %s AND time < %s
        ORDER BY time
    """, (employee, f"{date} 00:00:00", "2026-01-06 04:00:00"), as_dict=True)
    
    for c in checkins:
        print(f"  {c.name}: {c.time} {c.log_type} | shift_actual_end={c.shift_actual_end} | att={c.attendance}")
    
    print(f"\n修复完成！现在运行自动考勤...")
    
    # 5. 触发自动考勤
    shift_doc = frappe.get_doc("Shift Type", "统一班次")
    shift_doc.process_auto_attendance()
    
    # 6. 验证结果
    print(f"\nStep 6: 验证考勤结果...")
    new_attendance = frappe.db.sql("""
        SELECT name, attendance_date, in_time, out_time, working_hours
        FROM `tabAttendance`
        WHERE employee = %s AND attendance_date = %s
    """, (employee, date), as_dict=True)
    
    for att in new_attendance:
        print(f"  {att.name}: {att.attendance_date} | in={att.in_time} | out={att.out_time} | hours={att.working_hours}")
    
    return {"status": "success", "attendance": new_attendance}



