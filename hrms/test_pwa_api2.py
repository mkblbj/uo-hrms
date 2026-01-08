import frappe
from datetime import datetime
from frappe.utils import get_first_day, get_last_day, time_diff_in_hours

def test():
    # 找一个有员工记录的用户
    emp = frappe.db.get_value('Employee', {'status': 'Active'}, ['name', 'employee_name'], as_dict=True)
    print(f'测试员工: {emp.name} - {emp.employee_name}')

    today = datetime.now().date()
    month_start = get_first_day(today)
    month_end = get_last_day(today)

    # 旧方法：从打卡记录计算
    month_checkins = frappe.db.sql('''
        SELECT DATE(time) as date, log_type, MIN(time) as first_in, MAX(time) as last_out
        FROM `tabEmployee Checkin`
        WHERE employee = %s
        AND time BETWEEN %s AND %s
        GROUP BY DATE(time), log_type
        ORDER BY date, time
    ''', (emp.name, month_start, month_end), as_dict=True)
    
    old_hours = 0
    checkins_by_date = {}
    for c in month_checkins:
        date_str = str(c.date)
        if date_str not in checkins_by_date:
            checkins_by_date[date_str] = {'in': None, 'out': None}
        if c.log_type == 'IN' and not checkins_by_date[date_str]['in']:
            checkins_by_date[date_str]['in'] = c.first_in
        if c.log_type == 'OUT':
            checkins_by_date[date_str]['out'] = c.last_out
    
    for date, times in checkins_by_date.items():
        if times['in'] and times['out']:
            old_hours += time_diff_in_hours(times['out'], times['in'])

    # 新方法：从考勤表获取
    new_result = frappe.db.sql('''
        SELECT SUM(COALESCE(working_hours, 0)) as month_hours
        FROM `tabAttendance`
        WHERE employee = %s
        AND attendance_date BETWEEN %s AND %s
        AND docstatus = 1
    ''', (emp.name, month_start, month_end), as_dict=True)[0]
    
    new_hours = float(new_result.month_hours or 0)

    print(f'旧方法（打卡记录）: {round(old_hours, 2)}h')
    print(f'新方法（考勤表）: {new_hours}h')
    print(f'差异: {round(old_hours - new_hours, 2)}h')
