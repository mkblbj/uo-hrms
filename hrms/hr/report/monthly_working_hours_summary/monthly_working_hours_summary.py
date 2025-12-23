# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate
from calendar import monthrange


def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns(filters)
    data = get_data(filters)
    # Add HTML links to employee names
    add_employee_links(data, filters)
    # 不显示柱状图
    return columns, data, None, None


def get_columns(filters):
    return [
        {
            "label": _("员工编号"),
            "fieldname": "employee",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("员工姓名"),
            "fieldname": "employee_name",
            "fieldtype": "HTML",
            "width": 150,
        },
        {
            "label": _("部门"),
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 120,
        },
        {
            "label": _("出勤天数"),
            "fieldname": "present_days",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("缺勤天数"),
            "fieldname": "absent_days",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("请假天数"),
            "fieldname": "leave_days",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("半天"),
            "fieldname": "half_days",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("总工时"),
            "fieldname": "total_working_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 120,
        },
        {
            "label": _("迟到次数"),
            "fieldname": "late_entries",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": _("早退次数"),
            "fieldname": "early_exits",
            "fieldtype": "Int",
            "width": 100,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql(
        """
        SELECT 
            a.employee,
            a.employee_name,
            e.department,
            COUNT(CASE WHEN a.status = 'Present' THEN 1 END) as present_days,
            COUNT(CASE WHEN a.status = 'Absent' THEN 1 END) as absent_days,
            COUNT(CASE WHEN a.status = 'On Leave' THEN 1 END) as leave_days,
            COUNT(CASE WHEN a.status = 'Half Day' THEN 1 END) as half_days,
            SUM(COALESCE(a.working_hours, 0)) as total_working_hours,
            COUNT(CASE WHEN a.late_entry = 1 THEN 1 END) as late_entries,
            COUNT(CASE WHEN a.early_exit = 1 THEN 1 END) as early_exits
        FROM `tabAttendance` a
        LEFT JOIN `tabEmployee` e ON e.name = a.employee
        WHERE a.docstatus = 1
          {conditions}
        GROUP BY a.employee, a.employee_name, e.department
        ORDER BY a.employee_name
        """.format(conditions=conditions),
        filters,
        as_dict=True
    )
    
    return data


def add_employee_links(data, filters):
    """Add clickable links to employee names that navigate to detail report"""
    year = filters.get("year", "")
    month = filters.get("month", "")
    
    for row in data:
        detail_url = f"/desk/query-report/Employee%20Attendance%20Detail?employee={row.employee}&year={year}&month={month}"
        row["employee_name"] = f'<a href="{detail_url}" style="color: #2490ef; text-decoration: underline;">{row["employee_name"]}</a>'


def get_conditions(filters):
    conditions = []
    
    if filters.get("year") and filters.get("month"):
        year = int(filters.get("year"))
        month = int(filters.get("month"))
        _, last_day = monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        conditions.append("AND a.attendance_date BETWEEN %(start_date)s AND %(end_date)s")
        filters["start_date"] = start_date
        filters["end_date"] = end_date
    
    if filters.get("employee"):
        conditions.append("AND a.employee = %(employee)s")
    
    if filters.get("department"):
        conditions.append("AND e.department = %(department)s")
    
    if filters.get("company"):
        conditions.append("AND a.company = %(company)s")
    
    return " ".join(conditions)


def get_chart(data):
    if not data:
        return None
    
    # Top 10 employees by working hours
    sorted_data = sorted(data, key=lambda x: x.get("total_working_hours", 0), reverse=True)[:10]
    
    return {
        "data": {
            "labels": [d.get("employee_name", "") for d in sorted_data],
            "datasets": [
                {
                    "name": _("Working Hours"),
                    "values": [d.get("total_working_hours", 0) for d in sorted_data],
                }
            ],
        },
        "type": "bar",
        "colors": ["#7cd6fd"],
    }

