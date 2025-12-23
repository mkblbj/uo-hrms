"""
调试考勤计算
"""
import frappe
from datetime import datetime, timedelta
from hrms.hr.doctype.shift_type.shift_type import round_time_to_precision, calculate_lunch_overlap_hours


def debug_record(employee_name, date_str):
    """调试单条考勤记录"""
    
    # 获取考勤记录
    att = frappe.get_all("Attendance", 
        filters={
            "employee_name": employee_name,
            "attendance_date": date_str,
            "docstatus": 1
        },
        fields=["*"]
    )
    
    if not att:
        print(f"未找到 {employee_name} {date_str} 的考勤记录")
        return
    
    att = att[0]
    print(f"考勤记录: {att.employee_name} {att.attendance_date}")
    print(f"  签到时间: {att.in_time}")
    print(f"  签退时间: {att.out_time}")
    print(f"  工作时长: {att.working_hours}h")
    print(f"  班次: {att.shift}")
    
    # 获取原始打卡记录
    checkins = frappe.get_all("Employee Checkin",
        filters={
            "employee": att.employee,
            "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]]
        },
        fields=["time", "log_type", "shift", "attendance"],
        order_by="time"
    )
    
    print(f"\n原始打卡记录:")
    for c in checkins:
        print(f"  {c.time} - {c.log_type} (班次: {c.shift}, 考勤: {c.attendance})")
    
    # 模拟计算
    if att.in_time and att.out_time:
        in_time = frappe.utils.get_datetime(att.in_time)
        out_time = frappe.utils.get_datetime(att.out_time)
        
        print(f"\n模拟计算 (精度=15分钟):")
        
        # 取整
        rounded_in = round_time_to_precision(in_time, 15, 'up')
        rounded_out = round_time_to_precision(out_time, 15, 'down')
        
        print(f"  签到取整: {in_time.strftime('%H:%M:%S')} -> {rounded_in.strftime('%H:%M:%S')}")
        print(f"  签退取整: {out_time.strftime('%H:%M:%S')} -> {rounded_out.strftime('%H:%M:%S')}")
        
        # 计算工时
        raw_hours = (rounded_out - rounded_in).total_seconds() / 3600
        print(f"  取整后工时: {raw_hours:.4f}h")
        
        # 午休扣除
        from frappe.utils import get_time
        lunch_start = get_time("12:00:00")
        lunch_end = get_time("13:00:00")
        
        lunch_overlap = calculate_lunch_overlap_hours(rounded_in, rounded_out, lunch_start, lunch_end)
        print(f"  午休重叠: {lunch_overlap:.4f}h")
        
        after_lunch = raw_hours - lunch_overlap
        print(f"  扣除午休后: {after_lunch:.4f}h")
        
        # 最终取整
        precision_hours = 15 / 60  # 0.25
        final_hours = int(after_lunch / precision_hours) * precision_hours
        print(f"  最终取整: {final_hours:.2f}h")
        
        # 对比
        print(f"\n  数据库中的工时: {att.working_hours}h")
        print(f"  计算出的工时: {final_hours:.2f}h")
        
        if abs(att.working_hours - final_hours) > 0.01:
            print("  ❌ 不一致!")
        else:
            print("  ✅ 一致")


def check_shift_settings():
    """检查班次设置"""
    shift = frappe.get_doc("Shift Type", "统一班次")
    
    print("班次设置:")
    print(f"  enable_time_rounding: {shift.enable_time_rounding}")
    print(f"  rounding_precision: {shift.rounding_precision}")
    print(f"  enable_lunch_deduction: {shift.enable_lunch_deduction}")
    print(f"  lunch_start: {shift.lunch_start}")
    print(f"  lunch_end: {shift.lunch_end}")
    
    
def test_rounding():
    """测试取整函数"""
    from datetime import datetime
    
    test_cases = [
        (datetime(2025, 12, 1, 9, 0, 0), 15, 'up', "9:00 -> 9:00"),
        (datetime(2025, 12, 1, 9, 1, 0), 15, 'up', "9:01 -> 9:15"),
        (datetime(2025, 12, 1, 9, 12, 0), 15, 'up', "9:12 -> 9:15"),
        (datetime(2025, 12, 1, 9, 15, 0), 15, 'up', "9:15 -> 9:15"),
        (datetime(2025, 12, 1, 18, 0, 0), 15, 'down', "18:00 -> 18:00"),
        (datetime(2025, 12, 1, 17, 59, 0), 15, 'down', "17:59 -> 17:45"),
        (datetime(2025, 12, 1, 17, 47, 0), 15, 'down', "17:47 -> 17:45"),
        (datetime(2025, 12, 1, 17, 45, 0), 15, 'down', "17:45 -> 17:45"),
    ]
    
    print("取整测试:")
    for dt, precision, direction, expected in test_cases:
        result = round_time_to_precision(dt, precision, direction)
        status = "✅" if result.strftime("%H:%M") in expected else "❌"
        print(f"  {status} {expected}: 实际 {result.strftime('%H:%M')}")


def test_get_attendance(employee_name, date_str):
    """测试 get_attendance 方法"""
    
    # 获取考勤记录
    att = frappe.get_all("Attendance", 
        filters={
            "employee_name": employee_name,
            "attendance_date": date_str,
            "docstatus": 1
        },
        fields=["employee", "shift"]
    )
    
    if not att:
        print(f"未找到 {employee_name} {date_str} 的考勤记录")
        return
    
    att = att[0]
    
    # 获取班次
    shift = frappe.get_doc("Shift Type", att.shift)
    
    # 获取打卡记录
    logs = frappe.get_all("Employee Checkin",
        filters={
            "employee": att.employee,
            "time": ["between", [f"{date_str} 00:00:00", f"{date_str} 23:59:59"]],
            "shift": att.shift
        },
        fields=["*"],
        order_by="time"
    )
    
    if not logs:
        print("无打卡记录")
        return
    
    # 转成对象
    class Log:
        pass
    
    log_objects = []
    for l in logs:
        obj = Log()
        for k, v in l.items():
            setattr(obj, k, v)
        # 设置 shift_start 和 shift_end
        obj.shift_start = frappe.utils.get_datetime(f"{date_str} {shift.start_time}")
        obj.shift_end = frappe.utils.get_datetime(f"{date_str} {shift.end_time}")
        log_objects.append(obj)
    
    print(f"打卡记录数: {len(log_objects)}")
    for l in log_objects:
        print(f"  {l.time} - {l.log_type}")
    
    # 调用 get_attendance
    result = shift.get_attendance(log_objects)
    
    print(f"\nget_attendance 返回值:")
    print(f"  status: {result[0]}")
    print(f"  working_hours: {result[1]}")
    print(f"  late_entry: {result[2]}")
    print(f"  early_exit: {result[3]}")
    print(f"  in_time: {result[4]}")
    print(f"  out_time: {result[5]}")

