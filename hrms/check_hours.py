import frappe
from datetime import datetime
from frappe.utils import get_first_day, get_last_day

def check():
    # 员工 44 温 剛
    employee = '44'
    today = datetime.now().date()
    month_start = get_first_day(today)
    month_end = get_last_day(today)
    
    # 从考勤表获取
    result = frappe.db.sql('''
        SELECT SUM(COALESCE(working_hours, 0)) as total_hours
        FROM tabAttendance
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
    ''', (employee, month_start, month_end), as_dict=True)[0]
    
    print(f'员工 {employee} 本月工时（考勤表）: {result.total_hours}')
    print(f'round(2): {round(float(result.total_hours or 0), 2)}')
