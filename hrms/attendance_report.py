"""
员工考勤工时报表
"""
import frappe
from frappe.utils import getdate, add_months, get_first_day, get_last_day
import csv
import os


def get_monthly_working_hours(employee=None, year=None, month=None):
    """
    获取员工月度工时汇总
    
    Args:
        employee: 员工ID（可选，不传则查询所有员工）
        year: 年份（默认当前年）
        month: 月份（默认当前月）
    
    Returns:
        员工工时汇总列表
    """
    from datetime import date
    
    today = date.today()
    year = int(year) if year else today.year
    month = int(month) if month else today.month
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    filters = {
        "attendance_date": [">=", start_date],
        "attendance_date_end": ["<", end_date],
        "docstatus": 1
    }
    
    if employee:
        filters["employee"] = employee
    
    # 查询考勤数据
    sql = """
        SELECT 
            a.employee,
            a.employee_name,
            COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present_days,
            COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as absent_days,
            COUNT(CASE WHEN a.status = 'On Leave' THEN 1 END) as leave_days,
            COUNT(CASE WHEN a.status = 'Half Day' THEN 1 END) as half_days,
            SUM(COALESCE(a.working_hours, 0)) as total_working_hours,
            COUNT(*) as total_records
        FROM `tabAttendance` a
        WHERE a.docstatus = 1
          AND a.attendance_date >= %(start_date)s
          AND a.attendance_date < %(end_date)s
          {employee_filter}
        GROUP BY a.employee, a.employee_name
        ORDER BY a.employee_name
    """.format(
        employee_filter="AND a.employee = %(employee)s" if employee else ""
    )
    
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "employee": employee
    }
    
    result = frappe.db.sql(sql, params, as_dict=True)
    
    print("=" * 80)
    print(f"员工月度工时汇总 - {year}年{month}月")
    print("=" * 80)
    print(f"{'员工':<15} {'姓名':<12} {'出勤':>6} {'缺勤':>6} {'请假':>6} {'半天':>6} {'总工时':>10}")
    print("-" * 80)
    
    total_hours = 0
    for r in result:
        hours = float(r.total_working_hours or 0)
        total_hours += hours
        print(f"{r.employee:<15} {r.employee_name:<12} {r.present_days:>6} {r.absent_days:>6} {r.leave_days:>6} {r.half_days:>6} {hours:>10.2f}h")
    
    print("-" * 80)
    print(f"{'合计':<30} {'':<24} {total_hours:>10.2f}h")
    print("=" * 80)
    
    return result


def get_employee_daily_detail(employee, year=None, month=None):
    """
    获取单个员工的每日考勤明细
    
    Args:
        employee: 员工ID
        year: 年份
        month: 月份
    """
    from datetime import date
    
    today = date.today()
    year = int(year) if year else today.year
    month = int(month) if month else today.month
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    sql = """
        SELECT 
            a.attendance_date,
            a.status,
            TIME(a.in_time) as in_time,
            TIME(a.out_time) as out_time,
            a.working_hours,
            a.late_entry,
            a.early_exit
        FROM `tabAttendance` a
        WHERE a.docstatus = 1
          AND a.employee = %(employee)s
          AND a.attendance_date >= %(start_date)s
          AND a.attendance_date < %(end_date)s
        ORDER BY a.attendance_date
    """
    
    result = frappe.db.sql(sql, {
        "employee": employee,
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)
    
    # 获取员工姓名
    emp_name = frappe.db.get_value("Employee", employee, "employee_name")
    
    print("=" * 90)
    print(f"员工考勤明细 - {employee} {emp_name} - {year}年{month}月")
    print("=" * 90)
    print(f"{'日期':<12} {'状态':<10} {'签到':>10} {'签退':>10} {'工时':>8} {'迟到':>6} {'早退':>6}")
    print("-" * 90)
    
    total_hours = 0
    for r in result:
        hours = float(r.working_hours or 0)
        total_hours += hours
        
        in_time = str(r.in_time)[:5] if r.in_time else "-"
        out_time = str(r.out_time)[:5] if r.out_time else "-"
        late = "是" if r.late_entry else ""
        early = "是" if r.early_exit else ""
        
        print(f"{str(r.attendance_date):<12} {r.status:<10} {in_time:>10} {out_time:>10} {hours:>8.2f}h {late:>6} {early:>6}")
    
    print("-" * 90)
    print(f"{'合计':<12} {'':<20} {'':<10} {'':<10} {total_hours:>8.2f}h")
    print("=" * 90)
    
    return result


def export_monthly_attendance(year=None, month=None, employee=None, output_dir=None):
    """
    导出月度考勤表为 CSV
    
    Args:
        year: 年份
        month: 月份
        employee: 员工ID（可选）
        output_dir: 输出目录（默认为 /tmp）
    
    Returns:
        导出文件路径
    """
    from datetime import date
    
    today = date.today()
    year = int(year) if year else today.year
    month = int(month) if month else today.month
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    sql = """
        SELECT 
            a.employee as 员工编号,
            a.employee_name as 员工姓名,
            a.attendance_date as 考勤日期,
            a.status as 状态,
            TIME(a.in_time) as 签到时间,
            TIME(a.out_time) as 签退时间,
            a.working_hours as 工作时长,
            a.late_entry as 迟到,
            a.early_exit as 早退,
            a.shift as 班次
        FROM `tabAttendance` a
        WHERE a.docstatus = 1
          AND a.attendance_date >= %(start_date)s
          AND a.attendance_date < %(end_date)s
          {employee_filter}
        ORDER BY a.employee, a.attendance_date
    """.format(
        employee_filter="AND a.employee = %(employee)s" if employee else ""
    )
    
    result = frappe.db.sql(sql, {
        "start_date": start_date,
        "end_date": end_date,
        "employee": employee
    }, as_dict=True)
    
    if not result:
        print("没有找到考勤记录")
        return None
    
    # 生成文件名
    output_dir = output_dir or "/tmp"
    emp_suffix = f"_{employee}" if employee else "_all"
    filename = f"attendance_{year}{month:02d}{emp_suffix}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # 写入 CSV
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=result[0].keys())
        writer.writeheader()
        writer.writerows(result)
    
    print(f"✅ 已导出 {len(result)} 条记录到: {filepath}")
    return filepath


def export_monthly_summary(year=None, month=None, output_dir=None):
    """
    导出月度工时汇总为 CSV
    
    Args:
        year: 年份
        month: 月份
        output_dir: 输出目录
    
    Returns:
        导出文件路径
    """
    from datetime import date
    
    today = date.today()
    year = int(year) if year else today.year
    month = int(month) if month else today.month
    
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    sql = """
        SELECT 
            a.employee as 员工编号,
            a.employee_name as 员工姓名,
            COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as 出勤天数,
            COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as 缺勤天数,
            COUNT(CASE WHEN a.status = 'On Leave' THEN 1 END) as 请假天数,
            COUNT(CASE WHEN a.status = 'Half Day' THEN 1 END) as 半天天数,
            SUM(COALESCE(a.working_hours, 0)) as 总工时,
            COUNT(CASE WHEN a.late_entry = 1 THEN 1 END) as 迟到次数,
            COUNT(CASE WHEN a.early_exit = 1 THEN 1 END) as 早退次数
        FROM `tabAttendance` a
        WHERE a.docstatus = 1
          AND a.attendance_date >= %(start_date)s
          AND a.attendance_date < %(end_date)s
        GROUP BY a.employee, a.employee_name
        ORDER BY a.employee_name
    """
    
    result = frappe.db.sql(sql, {
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)
    
    if not result:
        print("没有找到考勤记录")
        return None
    
    # 生成文件名
    output_dir = output_dir or "/tmp"
    filename = f"attendance_summary_{year}{month:02d}.csv"
    filepath = os.path.join(output_dir, filename)
    
    # 写入 CSV
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=result[0].keys())
        writer.writeheader()
        writer.writerows(result)
    
    print(f"✅ 已导出 {len(result)} 条记录到: {filepath}")
    return filepath


