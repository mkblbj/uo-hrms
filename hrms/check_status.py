"""检查迁移状态"""
import frappe


def update_all_checkins():
    """强制更新所有打卡记录到统一班次"""
    shift = frappe.get_doc("Shift Type", "统一班次")
    start_time = str(shift.start_time)
    end_time = str(shift.end_time)
    
    # 统计更新前
    before = frappe.db.sql("""
        SELECT shift, COUNT(*) FROM `tabEmployee Checkin` 
        WHERE shift != '统一班次' OR shift IS NULL
        GROUP BY shift
    """)
    
    total_before = sum(r[1] for r in before)
    print(f"需要更新的记录: {total_before} 条")
    
    # 更新所有非统一班次的打卡记录
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET 
            shift = '统一班次',
            offshift = 0,
            shift_start = CONCAT(DATE(time), ' ', %s),
            shift_end = CONCAT(DATE(time), ' ', %s),
            shift_actual_start = CONCAT(DATE(time), ' ', %s),
            shift_actual_end = CONCAT(DATE(time), ' ', %s)
        WHERE shift != '统一班次' OR shift IS NULL
    """, (start_time, end_time, start_time, end_time))
    
    frappe.db.commit()
    
    print(f"✅ 已更新 {total_before} 条打卡记录到统一班次")


def check():
    """检查当前班次分配和打卡记录状态"""
    print("=" * 60)
    print("当前状态检查")
    print("=" * 60)
    
    # 1. 班次分配统计
    print("\n📋 班次分配统计 (docstatus=1):")
    result = frappe.db.sql("""
        SELECT shift_type, COUNT(*) as count 
        FROM `tabShift Assignment` 
        WHERE docstatus=1 
        GROUP BY shift_type
        ORDER BY count DESC
    """, as_dict=True)
    
    for r in result:
        print(f"   {r.shift_type}: {r.count} 个")
    
    total = sum(r.count for r in result)
    print(f"   总计: {total} 个")
    
    # 2. 打卡记录统计
    print("\n📋 打卡记录统计:")
    
    # 按班次分组
    checkin_by_shift = frappe.db.sql("""
        SELECT 
            COALESCE(shift, '无班次') as shift_name,
            COUNT(*) as count
        FROM `tabEmployee Checkin`
        GROUP BY shift
        ORDER BY count DESC
    """, as_dict=True)
    
    for r in checkin_by_shift:
        print(f"   {r.shift_name}: {r.count} 条")
    
    # offshift 统计
    offshift_count = frappe.db.count("Employee Checkin", {"offshift": 1})
    print(f"\n   其中 offshift=1: {offshift_count} 条")
    
    # 无考勤关联统计
    no_attendance = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabEmployee Checkin`
        WHERE attendance IS NULL OR attendance = ''
    """)[0][0]
    print(f"   无考勤关联: {no_attendance} 条")
    
    print("\n" + "=" * 60)

