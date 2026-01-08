import frappe
from datetime import datetime
from frappe.utils import get_first_day, get_last_day

def test():
    # 找一个有员工记录的用户
    emp = frappe.db.get_value('Employee', {'status': 'Active'}, ['name', 'employee_name'], as_dict=True)
    print(f'测试员工: {emp.name} - {emp.employee_name}')

    today = datetime.now().date()
    month_start = get_first_day(today)
    month_end = get_last_day(today)

    # 从考勤表获取工时
    result = frappe.db.sql('''
        SELECT SUM(working_hours) as total_hours
        FROM tabAttendance
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
    ''', (emp.name, month_start, month_end), as_dict=True)[0]

    print(f'本月工时（考勤表）: {result.total_hours}h')
