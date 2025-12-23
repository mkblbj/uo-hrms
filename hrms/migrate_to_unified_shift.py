"""
阶段4: 历史数据迁移脚本
- 取消所有现有班次分配
- 给所有活跃员工批量分配"统一班次"
- 更新历史 offshift 打卡记录
"""

import frappe
from frappe.utils import today, getdate, now_datetime

SHIFT_NAME = "统一班次"


def execute():
    """运行完整迁移（保留现有班次分配）"""
    print("=" * 60)
    print("开始迁移到统一班次")
    print("=" * 60)
    
    # 验证班次存在
    if not frappe.db.exists("Shift Type", SHIFT_NAME):
        frappe.throw(f"请先创建班次: {SHIFT_NAME}")
    
    shift = frappe.get_doc("Shift Type", SHIFT_NAME)
    
    # 1. 批量分配班次给活跃员工
    print("\n[步骤1] 创建班次分配...")
    created, skipped = create_shift_assignments(shift)
    
    # 2. 更新历史 offshift 打卡记录
    print("\n[步骤2] 更新历史打卡记录...")
    updated = update_offshift_checkins(shift)
    
    frappe.db.commit()
    
    print("\n" + "=" * 60)
    print("✅ 迁移完成!")
    print(f"   - 新建班次分配: {created} 个")
    print(f"   - 跳过(已有分配): {skipped} 个")
    print(f"   - 更新打卡记录: {updated} 条")
    print("=" * 60)
    
    return {
        "created_assignments": created,
        "skipped_assignments": skipped,
        "updated_checkins": updated
    }


def full_migration():
    """完整迁移：取消所有现有班次，全部改用统一班次"""
    print("=" * 60)
    print("完整迁移：取消所有班次，全部改用统一班次")
    print("=" * 60)
    
    # 验证班次存在
    if not frappe.db.exists("Shift Type", SHIFT_NAME):
        frappe.throw(f"请先创建班次: {SHIFT_NAME}")
    
    shift = frappe.get_doc("Shift Type", SHIFT_NAME)
    
    # 1. 取消所有现有班次分配
    print("\n[步骤1] 取消所有现有班次分配...")
    cancelled = cancel_all_shift_assignments()
    
    # 2. 给所有活跃员工分配统一班次
    print("\n[步骤2] 分配统一班次给所有员工...")
    created, skipped = create_shift_assignments(shift)
    
    # 3. 更新所有打卡记录关联到统一班次
    print("\n[步骤3] 更新所有打卡记录...")
    updated = update_all_checkins_to_unified_shift(shift)
    
    frappe.db.commit()
    
    print("\n" + "=" * 60)
    print("✅ 完整迁移完成!")
    print(f"   - 取消旧班次分配: {cancelled} 个")
    print(f"   - 新建班次分配: {created} 个")
    print(f"   - 更新打卡记录: {updated} 条")
    print("=" * 60)
    
    return {
        "cancelled_assignments": cancelled,
        "created_assignments": created,
        "updated_checkins": updated
    }


def cancel_all_shift_assignments():
    """取消所有现有的班次分配"""
    
    # 获取所有已提交的班次分配（排除统一班次）
    assignments = frappe.get_all("Shift Assignment",
        filters={
            "docstatus": 1,
            "shift_type": ["!=", SHIFT_NAME]
        },
        fields=["name", "employee", "shift_type"]
    )
    
    print(f"   发现 {len(assignments)} 个非统一班次分配需要取消")
    
    cancelled = 0
    for a in assignments:
        try:
            doc = frappe.get_doc("Shift Assignment", a.name)
            doc.flags.ignore_permissions = True
            doc.cancel()
            cancelled += 1
            print(f"   ✓ 取消: {a.employee} - {a.shift_type}")
        except Exception as e:
            print(f"   ✗ 失败: {a.name} - {str(e)[:50]}")
    
    # 也取消统一班次的旧分配（如果有的话，为了重新分配）
    unified_assignments = frappe.get_all("Shift Assignment",
        filters={
            "docstatus": 1,
            "shift_type": SHIFT_NAME
        },
        pluck="name"
    )
    
    for name in unified_assignments:
        try:
            doc = frappe.get_doc("Shift Assignment", name)
            doc.flags.ignore_permissions = True
            doc.cancel()
            cancelled += 1
        except Exception as e:
            print(f"   ✗ 失败: {name} - {str(e)[:50]}")
    
    print(f"   共取消 {cancelled} 个班次分配")
    return cancelled


def update_all_checkins_to_unified_shift(shift):
    """更新所有打卡记录到统一班次"""
    
    start_time = str(shift.start_time)
    end_time = str(shift.end_time)
    
    # 统计需要更新的记录
    # 1. offshift 记录
    offshift_count = frappe.db.count("Employee Checkin", {
        "offshift": 1,
        "attendance": ["is", "not set"]
    })
    
    # 2. 其他班次的记录（无考勤关联的）
    other_shift_count = frappe.db.sql("""
        SELECT COUNT(*) FROM `tabEmployee Checkin`
        WHERE (shift != %s OR shift IS NULL)
          AND (attendance IS NULL OR attendance = '')
    """, (SHIFT_NAME,))[0][0]
    
    print(f"   offshift 记录: {offshift_count} 条")
    print(f"   其他班次记录: {other_shift_count} 条")
    
    # 批量更新所有未关联考勤的打卡记录
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET 
            shift = %(shift_name)s,
            offshift = 0,
            shift_start = CONCAT(DATE(time), ' ', %(start_time)s),
            shift_end = CONCAT(DATE(time), ' ', %(end_time)s),
            shift_actual_start = CONCAT(DATE(time), ' ', %(start_time)s),
            shift_actual_end = CONCAT(DATE(time), ' ', %(end_time)s)
        WHERE (attendance IS NULL OR attendance = '')
    """, {
        "shift_name": SHIFT_NAME,
        "start_time": start_time,
        "end_time": end_time
    })
    
    # 获取更新数量
    updated = offshift_count + other_shift_count
    print(f"   已更新 {updated} 条打卡记录")
    return updated


def create_shift_assignments(shift):
    """为所有活跃员工创建班次分配（如果还没有）"""
    
    # 获取所有活跃员工
    employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "date_of_joining", "company"]
    )
    
    created = 0
    skipped = 0
    
    for emp in employees:
        # 检查是否已有该班次的有效分配
        existing = frappe.db.exists("Shift Assignment", {
            "employee": emp.name,
            "shift_type": SHIFT_NAME,
            "docstatus": 1,
            "status": "Active"
        })
        
        if existing:
            skipped += 1
            continue
        
        # 创建新的班次分配
        try:
            start_date = emp.date_of_joining or getdate("2020-01-01")
            
            assignment = frappe.new_doc("Shift Assignment")
            assignment.employee = emp.name
            assignment.shift_type = SHIFT_NAME
            assignment.company = emp.company
            assignment.start_date = start_date
            assignment.status = "Active"
            # end_date 留空表示永久生效
            assignment.flags.ignore_permissions = True
            assignment.insert()
            assignment.submit()
            
            created += 1
            print(f"   ✓ {emp.name} - {emp.employee_name}")
            
        except Exception as e:
            print(f"   ✗ {emp.name} - {emp.employee_name}: {str(e)}")
    
    print(f"\n   班次分配: 创建 {created}, 跳过 {skipped}")
    return created, skipped


def update_offshift_checkins(shift):
    """更新历史 offshift 打卡记录，关联到统一班次"""
    
    # 获取班次时间配置
    start_time = str(shift.start_time)
    end_time = str(shift.end_time)
    
    # 计算实际有效时间范围
    # actual_start = start_time - begin_check_in_before_shift_start_time
    # actual_end = end_time + allow_check_out_after_shift_end_time
    from datetime import timedelta
    from frappe.utils import get_time
    
    start_t = get_time(start_time)
    end_t = get_time(end_time)
    
    # 简化处理：使用班次开始/结束时间作为 actual 时间
    # 因为我们的班次范围已经足够宽
    
    # 查询需要更新的记录数
    count_before = frappe.db.count("Employee Checkin", {"offshift": 1, "attendance": ["is", "not set"]})
    print(f"   发现 {count_before} 条 offshift 打卡记录")
    
    if count_before == 0:
        print("   无需更新")
        return 0
    
    # 批量更新
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET 
            shift = %(shift_name)s,
            offshift = 0,
            shift_start = CONCAT(DATE(time), ' ', %(start_time)s),
            shift_end = CONCAT(DATE(time), ' ', %(end_time)s),
            shift_actual_start = CONCAT(DATE(time), ' ', %(start_time)s),
            shift_actual_end = CONCAT(DATE(time), ' ', %(end_time)s)
        WHERE offshift = 1 
          AND (attendance IS NULL OR attendance = '')
    """, {
        "shift_name": SHIFT_NAME,
        "start_time": start_time,
        "end_time": end_time
    })
    
    # 获取实际更新数量
    count_after = frappe.db.count("Employee Checkin", {"offshift": 1, "attendance": ["is", "not set"]})
    updated = count_before - count_after
    
    print(f"   已更新 {updated} 条记录")
    return updated


def preview():
    """预览将要迁移的数据（不实际修改）"""
    print("=" * 60)
    print("迁移预览（不会修改数据）")
    print("=" * 60)
    
    # 统计活跃员工
    active_employees = frappe.db.count("Employee", {"status": "Active"})
    print(f"\n活跃员工数: {active_employees}")
    
    # 统计已有班次分配的员工
    existing_assignments = frappe.db.sql("""
        SELECT COUNT(DISTINCT employee) 
        FROM `tabShift Assignment` 
        WHERE shift_type = %s AND docstatus = 1 AND status = 'Active'
    """, (SHIFT_NAME,))[0][0]
    print(f"已有'{SHIFT_NAME}'分配: {existing_assignments}")
    print(f"需新建分配: {active_employees - existing_assignments}")
    
    # 统计 offshift 打卡记录
    offshift_checkins = frappe.db.count("Employee Checkin", {"offshift": 1, "attendance": ["is", "not set"]})
    print(f"\nOffshift 打卡记录: {offshift_checkins}")
    
    # 按日期分布
    if offshift_checkins > 0:
        date_dist = frappe.db.sql("""
            SELECT DATE(time) as date, COUNT(*) as count
            FROM `tabEmployee Checkin`
            WHERE offshift = 1 AND (attendance IS NULL OR attendance = '')
            GROUP BY DATE(time)
            ORDER BY date DESC
            LIMIT 10
        """, as_dict=True)
        
        print("\n最近的 offshift 记录:")
        for d in date_dist:
            print(f"   {d.date}: {d.count} 条")
    
    print("\n" + "=" * 60)


def rollback():
    """回滚迁移（如果需要）"""
    print("=" * 60)
    print("开始回滚迁移")
    print("=" * 60)
    
    # 1. 回滚 offshift 状态
    print("\n[步骤1] 恢复打卡记录的 offshift 状态...")
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET 
            shift = NULL,
            offshift = 1,
            shift_start = NULL,
            shift_end = NULL,
            shift_actual_start = NULL,
            shift_actual_end = NULL
        WHERE shift = %s
    """, (SHIFT_NAME,))
    
    # 2. 取消班次分配
    print("[步骤2] 取消班次分配...")
    assignments = frappe.get_all("Shift Assignment",
        filters={"shift_type": SHIFT_NAME, "docstatus": 1},
        pluck="name"
    )
    
    for name in assignments:
        try:
            doc = frappe.get_doc("Shift Assignment", name)
            doc.flags.ignore_permissions = True
            doc.cancel()
        except Exception as e:
            print(f"   跳过 {name}: {str(e)}")
    
    frappe.db.commit()
    
    print(f"\n✅ 回滚完成!")
    print(f"   - 取消班次分配: {len(assignments)} 个")

