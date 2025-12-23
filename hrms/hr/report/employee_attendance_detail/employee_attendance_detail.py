# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, formatdate
from calendar import monthrange


def execute(filters=None):
    filters = frappe._dict(filters or {})
    
    if not filters.get("employee"):
        frappe.msgprint(_("Please select an employee"), alert=True)
        return [], []
    
    columns = get_columns(filters)
    data = get_data(filters)
    summary = get_summary(data)
    # 不显示图表，让表格更清晰
    return columns, data, summary, None


def get_columns(filters):
    return [
        {
            "label": _("日期"),
            "fieldname": "attendance_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("星期"),
            "fieldname": "day_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": _("状态"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("签到"),
            "fieldname": "in_time",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("签退"),
            "fieldname": "out_time",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": _("工时"),
            "fieldname": "working_hours",
            "fieldtype": "Float",
            "precision": 2,
            "width": 100,
        },
        {
            "label": _("迟到"),
            "fieldname": "late_entry",
            "fieldtype": "Data",
            "width": 60,
        },
        {
            "label": _("早退"),
            "fieldname": "early_exit",
            "fieldtype": "Data",
            "width": 60,
        },
        {
            "label": _("班次"),
            "fieldname": "shift",
            "fieldtype": "Link",
            "options": "Shift Type",
            "width": 100,
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)
    
    data = frappe.db.sql(
        """
        SELECT 
            a.attendance_date,
            DAYNAME(a.attendance_date) as day_name,
            a.status,
            TIME(a.in_time) as in_time,
            TIME(a.out_time) as out_time,
            a.working_hours,
            CASE WHEN a.late_entry = 1 THEN '✓' ELSE '' END as late_entry,
            CASE WHEN a.early_exit = 1 THEN '✓' ELSE '' END as early_exit,
            a.shift
        FROM `tabAttendance` a
        WHERE a.docstatus = 1
          AND a.employee = %(employee)s
          {conditions}
        ORDER BY a.attendance_date
        """.format(conditions=conditions),
        filters,
        as_dict=True
    )
    
    # Format time fields
    for row in data:
        if row.in_time:
            row.in_time = str(row.in_time)[:5]  # HH:MM
        else:
            row.in_time = "-"
        if row.out_time:
            row.out_time = str(row.out_time)[:5]  # HH:MM
        else:
            row.out_time = "-"
        
        # Translate day name
        day_map = {
            "Monday": _("Mon"),
            "Tuesday": _("Tue"),
            "Wednesday": _("Wed"),
            "Thursday": _("Thu"),
            "Friday": _("Fri"),
            "Saturday": _("Sat"),
            "Sunday": _("Sun"),
        }
        row.day_name = day_map.get(row.day_name, row.day_name)
    
    return data


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
    
    return " ".join(conditions)


def get_summary(data):
    if not data:
        return []
    
    present_days = sum(1 for d in data if d.status == "Present")
    absent_days = sum(1 for d in data if d.status == "Absent")
    leave_days = sum(1 for d in data if d.status == "On Leave")
    half_days = sum(1 for d in data if d.status == "Half Day")
    total_hours = sum(d.working_hours or 0 for d in data)
    late_entries = sum(1 for d in data if d.late_entry == "✓")
    early_exits = sum(1 for d in data if d.early_exit == "✓")
    
    return [
        {
            "value": present_days,
            "label": _("Present Days"),
            "indicator": "green",
            "datatype": "Int",
        },
        {
            "value": absent_days,
            "label": _("Absent Days"),
            "indicator": "red",
            "datatype": "Int",
        },
        {
            "value": leave_days,
            "label": _("Leave Days"),
            "indicator": "blue",
            "datatype": "Int",
        },
        {
            "value": round(total_hours, 2),
            "label": _("Total Working Hours"),
            "indicator": "orange",
            "datatype": "Float",
        },
        {
            "value": late_entries,
            "label": _("Late Entries"),
            "indicator": "yellow",
            "datatype": "Int",
        },
    ]


def get_chart(data):
    if not data:
        return None
    
    # Daily working hours chart
    dates = [str(d.attendance_date.day) for d in data if d.working_hours]
    hours = [d.working_hours for d in data if d.working_hours]
    
    if not dates:
        return None
    
    return {
        "data": {
            "labels": dates,
            "datasets": [
                {
                    "name": _("Working Hours"),
                    "values": hours,
                }
            ],
        },
        "type": "bar",
        "colors": ["#7cd6fd"],
        "height": 200,
    }

