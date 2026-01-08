import frappe

def verify():
    # 检查工时不是0.5倍数的记录
    sql = '''
        SELECT 
            employee_name,
            attendance_date,
            working_hours,
            MOD(working_hours * 2, 1) as remainder
        FROM tabAttendance
        WHERE docstatus = 1 
          AND working_hours > 0
          AND MOD(working_hours * 2, 1) != 0
        LIMIT 10
    '''
    
    bad_records = frappe.db.sql(sql, as_dict=True)
    
    if bad_records:
        print('❌ 发现工时不是0.5倍数的记录:')
        for r in bad_records:
            print(f'  - {r.employee_name} {r.attendance_date}: {r.working_hours}h')
    else:
        print('✅ 所有工时都是0.5的倍数（30分钟精度）')
    
    # 抽样查看
    print('\n抽样工时记录:')
    samples = frappe.db.sql('''
        SELECT 
            employee_name,
            attendance_date,
            TIME(in_time) as in_time,
            TIME(out_time) as out_time,
            working_hours
        FROM tabAttendance
        WHERE docstatus = 1 AND working_hours > 0
        ORDER BY RAND()
        LIMIT 8
    ''', as_dict=True)
    
    for r in samples:
        in_t = str(r.in_time)[:5] if r.in_time else '-'
        out_t = str(r.out_time)[:5] if r.out_time else '-'
        print(f'{r.employee_name}: {r.attendance_date} | {in_t} → {out_t} | {r.working_hours}h')
    
    # 员工44的本月工时
    result = frappe.db.sql('''
        SELECT SUM(working_hours) as total
        FROM tabAttendance
        WHERE employee = '44' AND docstatus = 1
        AND attendance_date >= '2025-12-01' AND attendance_date <= '2025-12-31'
    ''', as_dict=True)[0]
    print(f'\n员工44本月工时: {result.total}h')
