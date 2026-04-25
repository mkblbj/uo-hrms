"""
阶段5: 重新计算考勤
"""
import frappe
from frappe.utils import now_datetime, getdate


def execute():
    """重新处理自动考勤"""
    print("=" * 60)
    print("阶段5: 重新计算考勤")
    print("=" * 60)
    
    shift = frappe.get_doc("Shift Type", "统一班次")
    
    # 统计当前考勤状态
    before_count = frappe.db.count("Attendance", {"shift": "统一班次"})
    print(f"\n当前统一班次考勤记录: {before_count} 条")
    
    # 设置处理起始日期
    print(f"\n处理考勤起始日期: {shift.process_attendance_after}")
    
    # 更新 last_sync 时间触发重新处理
    shift.last_sync_of_checkin = now_datetime()
    shift.flags.ignore_permissions = True
    shift.save()
    
    print("开始处理自动考勤...")
    
    # 调用自动考勤处理
    shift.process_auto_attendance()
    
    frappe.db.commit()
    
    # 统计处理后的考勤
    after_count = frappe.db.count("Attendance", {"shift": "统一班次"})
    new_count = after_count - before_count
    
    print(f"\n✅ 考勤处理完成!")
    print(f"   - 新生成考勤: {new_count} 条")
    print(f"   - 统一班次考勤总数: {after_count} 条")
    
    # 检查未处理的打卡记录
    pending = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabEmployee Checkin`
        WHERE shift = '统一班次' AND (attendance IS NULL OR attendance = '')
    """)[0][0]
    
    print(f"   - 仍待处理打卡记录: {pending} 条")
    
    print("=" * 60)
    
    return {
        "new_attendance": new_count,
        "total_attendance": after_count,
        "pending_checkins": pending
    }


def check_attendance_samples():
    """检查几条考勤样本"""
    print("=" * 60)
    print("考勤样本检查（有打卡记录的）")
    print("=" * 60)
    
    # 获取有打卡的考勤记录
    samples = frappe.db.sql("""
        SELECT 
            a.employee,
            a.employee_name,
            a.attendance_date,
            a.status,
            a.working_hours,
            TIME(a.in_time) as in_time,
            TIME(a.out_time) as out_time
        FROM `tabAttendance` a
        WHERE a.shift = '统一班次'
          AND a.in_time IS NOT NULL
        ORDER BY a.attendance_date DESC
        LIMIT 15
    """, as_dict=True)
    
    print(f"\n最近 {len(samples)} 条有打卡的考勤记录:\n")
    
    for s in samples:
        print(f"  {s.attendance_date} | {s.employee_name}")
        print(f"    签到: {s.in_time} | 签退: {s.out_time}")
        print(f"    状态: {s.status} | 工时: {s.working_hours:.2f}h")
        print()
    
    # 统计工时分布
    print("\n工时分布统计:")
    dist = frappe.db.sql("""
        SELECT 
            CASE 
                WHEN working_hours = 0 THEN '0h'
                WHEN working_hours < 4 THEN '0-4h'
                WHEN working_hours < 8 THEN '4-8h'
                WHEN working_hours < 10 THEN '8-10h'
                ELSE '10h+'
            END as hours_range,
            COUNT(*) as count
        FROM `tabAttendance`
        WHERE shift = '统一班次'
        GROUP BY hours_range
        ORDER BY hours_range
    """, as_dict=True)
    
    for d in dist:
        print(f"   {d.hours_range}: {d.count} 条")
    
    print("=" * 60)

