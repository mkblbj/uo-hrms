# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, now_datetime
from datetime import datetime, timedelta


def batch_fix_january_attendance():
    """
    批量修复2026年1月份所有员工的考勤问题
    
    步骤：
    1. 确保所有活跃员工有统一班次分配
    2. 修复所有签到记录的 shift_actual_end
    3. 清除有问题的考勤和签到关联
    4. 重新运行自动考勤
    """
    
    print("=" * 60)
    print("开始批量修复2026年1月份考勤")
    print("=" * 60)
    
    # Step 1: 获取所有活跃员工
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        pluck="name"
    )
    print(f"\n[Step 1] 找到 {len(employees)} 名活跃员工")
    
    # Step 2: 为所有员工创建/更新统一班次分配（2026-01-01开始）
    print(f"\n[Step 2] 为所有员工分配统一班次...")
    shift_name = "统一班次"
    start_date = "2026-01-01"
    
    assigned_count = 0
    for emp in employees:
        # 检查是否已有从2026-01-01开始的班次分配
        existing = frappe.db.exists(
            "Shift Assignment",
            {
                "employee": emp,
                "shift_type": shift_name,
                "start_date": ["<=", start_date],
                "docstatus": 1,
                "status": "Active"
            }
        )
        
        if not existing:
            # 先取消该员工从1月1日开始的其他班次分配
            other_assignments = frappe.get_all(
                "Shift Assignment",
                filters={
                    "employee": emp,
                    "start_date": [">=", start_date],
                    "docstatus": 1
                },
                pluck="name"
            )
            for sa in other_assignments:
                doc = frappe.get_doc("Shift Assignment", sa)
                doc.flags.ignore_permissions = True
                doc.cancel()
            
            # 创建新的班次分配
            try:
                sa = frappe.new_doc("Shift Assignment")
                sa.employee = emp
                sa.shift_type = shift_name
                sa.start_date = start_date
                sa.status = "Active"
                sa.flags.ignore_permissions = True
                sa.insert()
                sa.submit()
                assigned_count += 1
            except Exception as e:
                print(f"  警告: 员工 {emp} 班次分配失败: {e}")
    
    print(f"  新分配班次: {assigned_count} 人")
    frappe.db.commit()
    
    # Step 3: 修复所有统一班次签到记录的 shift_actual_end
    print(f"\n[Step 3] 修复签到记录的 shift_actual_end...")
    
    # 统一班次: 06:00-23:00, 签退延长240分钟 = 次日03:00
    # shift_actual_end 应该是 shift_start 日期 + 27小时
    updated = frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET shift_actual_end = DATE_ADD(DATE(shift_start), INTERVAL 27 HOUR)
        WHERE shift = %s
        AND shift_actual_end IS NOT NULL
        AND shift_start >= %s
    """, (shift_name, start_date))
    
    affected_rows = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(f"  更新了 {affected_rows} 条签到记录")
    frappe.db.commit()
    
    # Step 4: 找出所有跨天签退但考勤异常的情况
    print(f"\n[Step 4] 查找跨天签退异常...")
    
    # 找出签退时间在凌晨(00:00-04:00)但没有关联考勤的记录
    problem_checkouts = frappe.db.sql("""
        SELECT DISTINCT c.employee, DATE(c.shift_start) as attendance_date
        FROM `tabEmployee Checkin` c
        WHERE c.shift = %s
        AND c.log_type = 'OUT'
        AND HOUR(c.time) < 4
        AND DATE(c.time) > DATE(c.shift_start)
        AND c.time >= %s
        AND (c.attendance IS NULL OR c.skip_auto_attendance = 1)
    """, (shift_name, f"{start_date} 00:00:00"), as_dict=True)
    
    print(f"  找到 {len(problem_checkouts)} 个异常跨天签退")
    
    # Step 5: 重置这些日期的考勤
    print(f"\n[Step 5] 重置异常考勤...")
    
    dates_to_fix = set()
    for pc in problem_checkouts:
        dates_to_fix.add((pc.employee, str(pc.attendance_date)))
    
    # 额外: 找出所有1月份工时为0但有签到签退的考勤
    zero_hour_attendance = frappe.db.sql("""
        SELECT a.employee, a.attendance_date
        FROM `tabAttendance` a
        WHERE a.attendance_date >= %s
        AND a.attendance_date <= '2026-01-31'
        AND a.working_hours = 0
        AND a.status = 'Present'
        AND a.in_time IS NOT NULL
    """, (start_date,), as_dict=True)
    
    for zha in zero_hour_attendance:
        dates_to_fix.add((zha.employee, str(zha.attendance_date)))
    
    print(f"  需要重置 {len(dates_to_fix)} 个员工-日期组合")
    
    # Step 6: 批量重置考勤
    print(f"\n[Step 6] 批量重置考勤...")
    
    reset_count = 0
    for emp, date in dates_to_fix:
        try:
            # 取消并删除该日期的考勤
            attendances = frappe.get_all(
                "Attendance",
                filters={"employee": emp, "attendance_date": date},
                pluck="name"
            )
            
            for att_name in attendances:
                att_doc = frappe.get_doc("Attendance", att_name)
                if att_doc.docstatus == 1:
                    att_doc.flags.ignore_permissions = True
                    att_doc.cancel()
                frappe.delete_doc("Attendance", att_name, force=True)
            
            # 清除相关签到的考勤关联和skip标志
            frappe.db.sql("""
                UPDATE `tabEmployee Checkin`
                SET attendance = NULL, skip_auto_attendance = 0
                WHERE employee = %s
                AND shift_start >= %s AND shift_start < %s
            """, (emp, f"{date} 00:00:00", f"{date} 23:59:59"))
            
            reset_count += 1
            
        except Exception as e:
            print(f"  警告: 重置 {emp} {date} 失败: {e}")
    
    print(f"  已重置 {reset_count} 个员工-日期组合")
    frappe.db.commit()
    
    # Step 7: 重新运行自动考勤
    print(f"\n[Step 7] 重新运行自动考勤...")
    
    shift_doc = frappe.get_doc("Shift Type", shift_name)
    shift_doc.process_auto_attendance()
    frappe.db.commit()
    
    print(f"  自动考勤处理完成")
    
    # Step 8: 验证结果
    print(f"\n[Step 8] 验证修复结果...")
    
    # 检查还有多少0工时的Present考勤
    remaining_issues = frappe.db.sql("""
        SELECT COUNT(*) as cnt
        FROM `tabAttendance`
        WHERE attendance_date >= %s
        AND attendance_date <= '2026-01-31'
        AND working_hours = 0
        AND status = 'Present'
        AND in_time IS NOT NULL
    """, (start_date,))[0][0]
    
    print(f"  剩余异常考勤: {remaining_issues} 条")
    
    # 统计1月份考勤情况
    stats = frappe.db.sql("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN working_hours > 0 THEN 1 ELSE 0 END) as with_hours,
            SUM(CASE WHEN out_time IS NOT NULL THEN 1 ELSE 0 END) as with_checkout
        FROM `tabAttendance`
        WHERE attendance_date >= %s AND attendance_date <= '2026-01-31'
        AND status = 'Present'
    """, (start_date,), as_dict=True)[0]
    
    print(f"\n1月份考勤统计:")
    print(f"  总出勤记录: {stats.total}")
    print(f"  有工时记录: {stats.with_hours}")
    print(f"  有签退记录: {stats.with_checkout}")
    
    print("\n" + "=" * 60)
    print("批量修复完成!")
    print("=" * 60)
    
    return {
        "employees": len(employees),
        "shift_assignments": assigned_count,
        "reset_count": reset_count,
        "remaining_issues": remaining_issues
    }


def fix_all_checkin_shift_actual_end():
    """修复所有统一班次签到记录的 shift_actual_end"""
    
    print("修复所有统一班次的 shift_actual_end...")
    
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET shift_actual_end = DATE_ADD(DATE(shift_start), INTERVAL 27 HOUR)
        WHERE shift = '统一班次'
        AND shift_actual_end IS NOT NULL
    """)
    
    affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    frappe.db.commit()
    
    print(f"已更新 {affected} 条记录")
    return affected


