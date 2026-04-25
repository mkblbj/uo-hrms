"""
重置考勤数据并重新计算
"""
import frappe


def delete_all_attendance():
    """删除所有考勤记录"""
    
    # 统计当前考勤数量
    count = frappe.db.count("Attendance")
    print(f"当前考勤记录数: {count}")
    
    if count == 0:
        print("没有考勤记录需要删除")
        return
    
    # 先取消提交的考勤（docstatus=1 -> docstatus=2）
    frappe.db.sql("""
        UPDATE `tabAttendance` 
        SET docstatus = 2 
        WHERE docstatus = 1
    """)
    print("✅ 已取消所有已提交的考勤")
    
    # 删除所有考勤记录
    frappe.db.sql("DELETE FROM `tabAttendance`")
    frappe.db.commit()
    
    # 确认删除
    remaining = frappe.db.count("Attendance")
    print(f"✅ 已删除所有考勤记录，剩余: {remaining}")


def reset_checkin_attendance_link():
    """重置 Employee Checkin 的 attendance 关联"""
    
    updated = frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET attendance = NULL
        WHERE attendance IS NOT NULL
    """)
    frappe.db.commit()
    
    count = frappe.db.count("Employee Checkin", {"attendance": ["is", "set"]})
    print(f"✅ 已清除 Employee Checkin 的 attendance 关联，剩余关联: {count}")


def reset_shift_sync_time():
    """重置班次的同步时间，确保重新处理所有打卡记录"""
    
    # 获取统一班次
    shift = frappe.get_doc("Shift Type", "统一班次")
    
    # 设置一个很早的时间，确保所有打卡记录都会被处理
    shift.process_attendance_after = "2024-01-01"
    shift.last_sync_of_checkin = None
    shift.save()
    frappe.db.commit()
    
    print(f"✅ 已重置班次同步时间: process_attendance_after = 2024-01-01")


def recalculate_attendance():
    """重新计算考勤"""
    from datetime import datetime
    
    shift = frappe.get_doc("Shift Type", "统一班次")
    
    # 确认班次设置
    print("\n班次设置:")
    print(f"  - 启用时间取整: {shift.enable_time_rounding}")
    print(f"  - 取整精度: {shift.rounding_precision} 分钟")
    print(f"  - 启用午休扣除: {shift.enable_lunch_deduction}")
    print(f"  - 午休时间: {shift.lunch_start} - {shift.lunch_end}")
    
    # 更新同步时间
    shift.last_sync_of_checkin = datetime.now()
    shift.save()
    frappe.db.commit()
    
    print("\n开始处理考勤...")
    shift.process_auto_attendance()
    
    # 统计结果
    count = frappe.db.count("Attendance", {"docstatus": 1})
    print(f"\n✅ 考勤处理完成，共生成 {count} 条考勤记录")


def full_reset():
    """完整重置流程"""
    print("=" * 60)
    print("开始重置考勤数据...")
    print("=" * 60)
    
    print("\n[1/4] 删除所有考勤记录...")
    delete_all_attendance()
    
    print("\n[2/4] 清除打卡记录的考勤关联...")
    reset_checkin_attendance_link()
    
    print("\n[3/4] 重置班次同步时间...")
    reset_shift_sync_time()
    
    print("\n[4/4] 重新计算考勤...")
    recalculate_attendance()
    
    print("\n" + "=" * 60)
    print("重置完成！")
    print("=" * 60)


def verify_working_hours():
    """验证工时计算是否正确（应该是0.25的倍数）"""
    
    # 检查工时不是0.25倍数的记录
    sql = """
        SELECT 
            employee,
            employee_name,
            attendance_date,
            working_hours,
            MOD(working_hours * 4, 1) as remainder
        FROM `tabAttendance`
        WHERE docstatus = 1 
          AND working_hours > 0
          AND MOD(working_hours * 4, 1) != 0
        LIMIT 20
    """
    
    bad_records = frappe.db.sql(sql, as_dict=True)
    
    if bad_records:
        print("❌ 发现工时不是0.25倍数的记录:")
        for r in bad_records:
            print(f"  - {r.employee_name} {r.attendance_date}: {r.working_hours}h")
    else:
        print("✅ 所有工时都是0.25的倍数")
    
    # 抽样查看几条记录
    print("\n抽样工时记录:")
    samples = frappe.db.sql("""
        SELECT 
            employee_name,
            attendance_date,
            TIME(in_time) as in_time,
            TIME(out_time) as out_time,
            working_hours
        FROM `tabAttendance`
        WHERE docstatus = 1 AND working_hours > 0
        ORDER BY RAND()
        LIMIT 10
    """, as_dict=True)
    
    print(f"{'员工':<12} {'日期':<12} {'签到':>8} {'签退':>8} {'工时':>8}")
    print("-" * 60)
    for r in samples:
        in_t = str(r.in_time)[:5] if r.in_time else "-"
        out_t = str(r.out_time)[:5] if r.out_time else "-"
        print(f"{r.employee_name:<12} {str(r.attendance_date):<12} {in_t:>8} {out_t:>8} {r.working_hours:>8.2f}h")

