"""
测试单条考勤记录的创建过程
"""
import frappe
from datetime import datetime


def test_single():
    """测试单条考勤创建"""
    
    # 删除现有考勤
    frappe.db.sql("""
        UPDATE `tabAttendance` SET docstatus=2 
        WHERE employee_name='温 剛' AND attendance_date='2025-12-02'
    """)
    frappe.db.sql("""
        DELETE FROM `tabAttendance` 
        WHERE employee_name='温 剛' AND attendance_date='2025-12-02'
    """)
    
    # 清除打卡记录的考勤关联
    frappe.db.sql("""
        UPDATE `tabEmployee Checkin`
        SET attendance = NULL
        WHERE employee = '44' AND DATE(time) = '2025-12-02'
    """)
    frappe.db.commit()
    
    # 获取班次
    shift = frappe.get_doc("Shift Type", "统一班次")
    
    # 获取打卡记录
    logs = frappe.get_all("Employee Checkin",
        filters={
            "employee": "44",  # 温剛
            "time": ["between", ["2025-12-02 00:00:00", "2025-12-02 23:59:59"]],
            "shift": "统一班次"
        },
        fields=["name", "employee", "log_type", "time", "shift", 
                "shift_start", "shift_end", "shift_actual_start", "shift_actual_end"],
        order_by="time"
    )
    
    print(f"打卡记录数: {len(logs)}")
    for l in logs:
        print(f"  {l.time} - {l.log_type}")
    
    # 手动调用 get_attendance
    result = shift.get_attendance(logs)
    status, working_hours, late_entry, early_exit, in_time, out_time = result
    
    print(f"\nget_attendance 返回:")
    print(f"  status: {status}")
    print(f"  working_hours: {working_hours} (type: {type(working_hours)})")
    print(f"  in_time: {in_time}")
    print(f"  out_time: {out_time}")
    
    # 手动创建考勤记录
    from hrms.hr.doctype.employee_checkin.employee_checkin import mark_attendance_and_link_log
    
    attendance_date = logs[0].time.date()
    
    print(f"\n调用 mark_attendance_and_link_log:")
    print(f"  working_hours 参数: {working_hours}")
    
    attendance_name = mark_attendance_and_link_log(
        logs,
        status,
        attendance_date,
        working_hours,
        late_entry,
        early_exit,
        in_time,
        out_time,
        shift.name,
        None  # overtime_type
    )
    
    print(f"\n考勤创建结果: {attendance_name}")
    
    # 读取数据库中的值
    if attendance_name:
        # 如果返回的是对象，获取名称
        if hasattr(attendance_name, 'name'):
            att_name = attendance_name.name
        else:
            att_name = str(attendance_name)
        
        db_working_hours = frappe.db.get_value("Attendance", att_name, "working_hours")
        print(f"\n数据库中的 working_hours: {db_working_hours}")
        
        if abs(float(db_working_hours or 0) - working_hours) > 0.001:
            print(f"❌ 不一致! 期望 {working_hours}, 实际 {db_working_hours}")
        else:
            print("✅ 一致")

