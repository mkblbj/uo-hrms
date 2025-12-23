# 统一班次与弹性工时实施方案

## 📋 需求概述

| 项目 | 说明 |
|------|------|
| 班次名称 | 统一班次 |
| 默认取整精度 | **15分钟** |
| 午休时间 | 12:00 - 13:00 |
| 取整规则 | 签到向后取整，签退向前取整 |

---

## 🔧 第一阶段：扩展 Shift Type 字段

### 1.1 新增字段清单

| 字段名 | 字段类型 | 标签 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| `flexible_hours_section` | Section Break | 弹性工时设置 | - | 分组标题 |
| `enable_time_rounding` | Check | 启用时间取整 | 0 | 总开关 |
| `rounding_precision` | Select | 取整精度(分钟) | 15 | 选项: 15\n30\n60 |
| `column_break_flex` | Column Break | - | - | 分栏 |
| `enable_lunch_deduction` | Check | 启用午休扣除 | 0 | 总开关 |
| `lunch_start` | Time | 午休开始 | 12:00:00 | depends_on: enable_lunch_deduction |
| `lunch_end` | Time | 午休结束 | 13:00:00 | depends_on: enable_lunch_deduction |

### 1.2 修改文件

```
apps/hrms/hrms/hr/doctype/shift_type/shift_type.json
```

### 1.3 字段位置

在 `overtime_section` 之前插入新的 section。

---

## 🔧 第二阶段：修改工时计算逻辑

### 2.1 新增函数

**文件**: `apps/hrms/hrms/hr/doctype/employee_checkin/employee_checkin.py`

```python
def round_time_to_precision(dt, precision_minutes, direction):
    """
    将时间取整到指定精度
    
    Args:
        dt: datetime 对象
        precision_minutes: 取整精度 (15, 30, 60)
        direction: 'up' (签到向后) 或 'down' (签退向前)
    
    Returns:
        取整后的 datetime
    
    Examples (precision=15):
        签到 9:00  → 9:00
        签到 9:01  → 9:15
        签到 9:12  → 9:15
        签到 9:16  → 9:30
        签退 18:00 → 18:00
        签退 17:59 → 17:45
        签退 17:47 → 17:45
    """


def calculate_lunch_overlap_hours(in_time, out_time, lunch_start, lunch_end):
    """
    计算工作时间与午休的重叠时长（小时）
    
    Args:
        in_time: 签到时间 (datetime)
        out_time: 签退时间 (datetime)
        lunch_start: 午休开始 (time)
        lunch_end: 午休结束 (time)
    
    Returns:
        float: 重叠小时数，无重叠返回 0
    
    Examples (午休 12:00-13:00):
        9:00-18:00  → 1.0 (扣除1小时)
        9:00-12:00  → 0.0 (不跨午休)
        13:00-18:00 → 0.0 (不跨午休)
        11:30-12:30 → 0.5 (部分重叠)
        11:30-14:00 → 1.0 (完全包含午休)
    """
```

### 2.2 修改 calculate_working_hours 函数

在现有函数返回前，应用取整和午休扣除逻辑。

**或者** 在 `shift_type.py` 的 `get_attendance` 方法中后处理 `total_working_hours`。

### 2.3 计算流程

```
┌─────────────────────────────────────────────────────────────┐
│                    工时计算流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  原始签到时间 ──► [取整] ──► 取整后签到时间                   │
│  原始签退时间 ──► [取整] ──► 取整后签退时间                   │
│                      │                                      │
│                      ▼                                      │
│         原始工作时长 = 取整签退 - 取整签到                    │
│                      │                                      │
│                      ▼                                      │
│              [午休扣除判断]                                   │
│                      │                                      │
│                      ▼                                      │
│         最终工作时长 = 原始时长 - 午休重叠时长                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 第三阶段：创建统一班次 ✅ 已完成 (2025-12-22)

### 3.1 班次配置

| 配置项 | 值 |
|--------|-----|
| 班次名称 | 统一班次 |
| 开始时间 | 06:00 |
| 结束时间 | 22:00 |
| 启用自动考勤 | ✅ |
| 签到签退判定方式 | 同一班次内交替记录签到/签退 |
| 工时计算方式 | 首次签到与末次签退 |
| 允许提前签到(分钟) | 120 (04:00起可签到) |
| 允许延后签退(分钟) | 120 (24:00前可签退) |
| **启用时间取整** | ✅ |
| **取整精度** | 15分钟 |
| **启用午休扣除** | ✅ |
| **午休开始** | 12:00 |
| **午休结束** | 13:00 |

> 注：06:00-22:00 覆盖大部分弹性工作时间，配合签到缓冲区实现 04:00-24:00 的有效打卡范围。

### 3.2 创建方式

通过脚本创建：`apps/hrms/hrms/create_unified_shift.py`

---

## 🔧 第四阶段：历史数据迁移

### 4.1 迁移脚本功能

1. 给所有活跃员工创建"统一班次"的 Shift Assignment
2. 更新所有 `offshift=1` 的 Employee Checkin 记录
3. 重新触发自动考勤计算

### 4.2 迁移脚本

**文件**: `apps/hrms/hrms/patches/post_install/migrate_to_unified_shift.py`

```python
import frappe
from frappe.utils import today, getdate

SHIFT_NAME = "统一班次"

def execute():
    """迁移到统一班次"""
    if not frappe.db.exists("Shift Type", SHIFT_NAME):
        frappe.throw(f"请先创建班次: {SHIFT_NAME}")
    
    shift = frappe.get_doc("Shift Type", SHIFT_NAME)
    
    # 1. 给活跃员工创建班次分配
    create_shift_assignments(shift)
    
    # 2. 更新历史 offshift checkin
    update_offshift_checkins(shift)
    
    frappe.db.commit()


def create_shift_assignments(shift):
    """为没有班次分配的活跃员工创建分配"""
    employees = frappe.get_all("Employee",
        filters={"status": "Active"},
        fields=["name", "date_of_joining"]
    )
    
    for emp in employees:
        # 检查是否已有有效的班次分配
        existing = frappe.db.exists("Shift Assignment", {
            "employee": emp.name,
            "shift_type": SHIFT_NAME,
            "docstatus": 1,
            "status": "Active"
        })
        
        if not existing:
            start_date = emp.date_of_joining or getdate("2020-01-01")
            
            assignment = frappe.new_doc("Shift Assignment")
            assignment.employee = emp.name
            assignment.shift_type = SHIFT_NAME
            assignment.start_date = start_date
            # end_date 留空表示永久生效
            assignment.insert()
            assignment.submit()
    
    print(f"已为 {len(employees)} 名员工检查/创建班次分配")


def update_offshift_checkins(shift):
    """更新历史 offshift 打卡记录"""
    
    # 获取班次时间
    start_time = shift.start_time  # "00:00:00"
    end_time = shift.end_time      # "23:59:00"
    
    # 计算 actual_start 和 actual_end
    # actual_start = start_time - begin_check_in_before_shift_start_time
    # actual_end = end_time + allow_check_out_after_shift_end_time
    # 对于全天班次，这些值基本等于 start_time 和 end_time
    
    updated = frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET 
            shift = %s,
            offshift = 0,
            shift_start = CONCAT(DATE(time), ' ', %s),
            shift_end = CONCAT(DATE(time), ' ', %s),
            shift_actual_start = CONCAT(DATE(time), ' ', %s),
            shift_actual_end = CONCAT(DATE(time), ' ', %s)
        WHERE offshift = 1 
          AND attendance IS NULL
    """, (SHIFT_NAME, start_time, end_time, start_time, end_time))
    
    affected_rows = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
    print(f"已更新 {affected_rows} 条 offshift 打卡记录")
```

### 4.3 运行迁移

```bash
# 方式1: 作为 patch 运行
bench --site [site-name] run-patch hrms.patches.post_install.migrate_to_unified_shift

# 方式2: 在 bench console 中运行
bench --site [site-name] console
>>> from hrms.patches.post_install.migrate_to_unified_shift import execute
>>> execute()
```

---

## 🔧 第五阶段：重新计算考勤

### 5.1 触发自动考勤

迁移后需要重新处理考勤：

```python
# 在 bench console 中
import frappe

shift = frappe.get_doc("Shift Type", "统一班次")

# 设置处理起始日期（根据历史数据范围调整）
shift.process_attendance_after = "2024-01-01"
shift.last_sync_of_checkin = frappe.utils.now_datetime()
shift.save()

# 触发自动考勤处理
shift.process_auto_attendance()
```

### 5.2 验证结果

检查 Attendance 记录是否正确生成：

```python
# 检查某个员工的考勤
frappe.get_all("Attendance", 
    filters={"employee": "HR-EMP-00001", "attendance_date": [">=", "2024-01-01"]},
    fields=["attendance_date", "status", "working_hours", "in_time", "out_time"]
)
```

---

## 📊 取整示例对照表（精度=15分钟）

### 签到取整（向后）

| 原始时间 | 取整结果 |
|---------|---------|
| 9:00 | 9:00 |
| 9:01 | 9:15 |
| 9:12 | 9:15 |
| 9:15 | 9:15 |
| 9:16 | 9:30 |
| 9:29 | 9:30 |
| 9:30 | 9:30 |
| 9:31 | 9:45 |

### 签退取整（向前）

| 原始时间 | 取整结果 |
|---------|---------|
| 18:00 | 18:00 |
| 17:59 | 17:45 |
| 17:47 | 17:45 |
| 17:45 | 17:45 |
| 17:44 | 17:30 |
| 17:31 | 17:30 |
| 17:30 | 17:30 |
| 17:29 | 17:15 |

### 综合计算示例

| 员工 | 原始签到 | 取整签到 | 原始签退 | 取整签退 | 原始时长 | 午休扣除 | 最终工时 |
|------|---------|---------|---------|---------|---------|---------|---------|
| A | 9:00 | 9:00 | 18:00 | 18:00 | 9.0h | 1.0h | **8.0h** |
| B | 9:12 | 9:15 | 18:00 | 18:00 | 8.75h | 1.0h | **7.75h** |
| C | 9:00 | 9:00 | 12:00 | 12:00 | 3.0h | 0h | **3.0h** |
| D | 13:00 | 13:00 | 18:00 | 18:00 | 5.0h | 0h | **5.0h** |
| E | 9:12 | 9:15 | 17:47 | 17:45 | 8.5h | 1.0h | **7.5h** |
| F | 8:50 | 9:00 | 18:10 | 18:00 | 9.0h | 1.0h | **8.0h** |
| G | 11:30 | 11:30 | 14:00 | 14:00 | 2.5h | 1.0h | **1.5h** |

---

## ✅ 实施检查清单

### 阶段一：字段扩展 ✅ 已完成 (2025-12-22)
- [x] 修改 `shift_type.json` 添加新字段
- [x] 运行 `bench migrate`
- [x] 验证新字段在界面显示

### 阶段二：计算逻辑 ✅ 已完成 (2025-12-22)
- [x] 添加 `round_time_to_precision` 函数
- [x] 添加 `calculate_lunch_overlap_hours` 函数
- [x] 修改 `get_attendance` 方法应用新逻辑
- [x] 单元测试验证计算正确性

### 阶段三：创建班次 ✅ 已完成 (2025-12-22)
- [x] 在系统中创建"统一班次"
- [x] 配置取整精度=15分钟
- [x] 配置午休=12:00-13:00
- [x] 启用自动考勤

### 阶段四：数据迁移 ✅ 已完成 (2025-12-22)
- [x] 备份数据库
- [x] 运行迁移脚本 (full_migration)
- [x] 取消所有旧班次分配
- [x] 26 个员工全部分配统一班次
- [x] 719 条打卡记录全部关联统一班次

### 阶段五：考勤重算 ✅ 已完成 (2025-12-22)
- [x] 设置 process_attendance_after = 2024-01-01
- [x] 运行 process_auto_attendance
- [x] 生成 1226 条考勤记录
- [x] 验证工时计算正确（签到向上取整、签退向下取整、午休扣除）

### 阶段六：验收 ✅ 已完成 (2025-12-22)
- [x] 26 个员工全部分配统一班次
- [x] 719 条打卡记录全部关联统一班次
- [x] 1226 条考勤记录已生成
- [x] 工时计算符合预期（时间取整 + 午休扣除）

---

## ⚠️ 注意事项

1. **数据备份**：迁移前务必备份 `tabEmployee Checkin`、`tabAttendance`、`tabShift Assignment` 表

2. **时区问题**：确保服务器时区和业务时区一致

3. **跨天打卡**：当前方案假设签到签退在同一天，跨天情况需要额外处理

4. **回滚方案**：
   ```sql
   -- 回滚 offshift 状态
   UPDATE `tabEmployee Checkin` 
   SET shift = NULL, offshift = 1 
   WHERE shift = '统一班次';
   
   -- 删除班次分配
   DELETE FROM `tabShift Assignment` WHERE shift_type = '统一班次';
   ```

5. **性能考虑**：如果历史数据量大，迁移脚本可能需要分批处理

---

## 📝 版本信息

| 项目 | 值 |
|------|-----|
| 文档版本 | 1.0 |
| 创建日期 | 2025-12-22 |
| 目标系统 | Frappe HRMS |


