// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Employee Attendance Detail"] = {
	filters: [
		{
			fieldname: "employee",
			label: __("员工"),
			fieldtype: "Link",
			options: "Employee",
			reqd: 1,
			get_query: function() {
				return {
					filters: {
						status: "Active"
					}
				};
			}
		},
		{
			fieldname: "year",
			label: __("年份"),
			fieldtype: "Select",
			options: get_year_options(),
			default: new Date().getFullYear(),
			reqd: 1
		},
		{
			fieldname: "month",
			label: __("月份"),
			fieldtype: "Select",
			options: get_month_options(),
			default: new Date().getMonth() + 1,
			reqd: 1
		}
	],
	
	// 颜色含义：
	// 状态：绿色=出勤，红色=缺勤，蓝色=请假，橙色=半天
	// 工时：绿色加粗=≥8小时
	// 迟到/早退：橙色=有标记
	// 星期：灰色=周末
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname === "status" && data) {
			if (data.status === "Present") {
				value = `<span style="color: green">${value}</span>`;
			} else if (data.status === "Absent") {
				value = `<span style="color: red">${value}</span>`;
			} else if (data.status === "On Leave") {
				value = `<span style="color: blue">${value}</span>`;
			} else if (data.status === "Half Day") {
				value = `<span style="color: orange">${value}</span>`;
			}
		}
		
		if (column.fieldname === "working_hours" && data && data.working_hours >= 8) {
			value = `<span style="color: green; font-weight: bold">${value}</span>`;
		}
		
		if (column.fieldname === "late_entry" && data && data.late_entry === "✓") {
			value = `<span style="color: orange">${value}</span>`;
		}
		
		if (column.fieldname === "early_exit" && data && data.early_exit === "✓") {
			value = `<span style="color: orange">${value}</span>`;
		}
		
		if (column.fieldname === "day_name" && data) {
			if (data.day_name === "Sat" || data.day_name === "Sun" || 
			    data.day_name === "Saturday" || data.day_name === "Sunday" ||
			    data.day_name === "周六" || data.day_name === "周日") {
				value = `<span style="color: #999">${value}</span>`;
			}
		}
		
		return value;
	}
};

function get_year_options() {
	let options = [];
	let current_year = new Date().getFullYear();
	for (let i = current_year; i >= current_year - 5; i--) {
		options.push(i);
	}
	return options;
}

function get_month_options() {
	return [
		{ value: 1, label: __("1月") },
		{ value: 2, label: __("2月") },
		{ value: 3, label: __("3月") },
		{ value: 4, label: __("4月") },
		{ value: 5, label: __("5月") },
		{ value: 6, label: __("6月") },
		{ value: 7, label: __("7月") },
		{ value: 8, label: __("8月") },
		{ value: 9, label: __("9月") },
		{ value: 10, label: __("10月") },
		{ value: 11, label: __("11月") },
		{ value: 12, label: __("12月") },
	];
}
