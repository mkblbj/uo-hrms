// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Working Hours Summary"] = {
	// 禁用树形结构，让表格正常展开
	tree: false,
	initial_depth: 0,
	filters: [
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
		},
		{
			fieldname: "company",
			label: __("公司"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		},
		{
			fieldname: "department",
			label: __("部门"),
			fieldtype: "Link",
			options: "Department"
		},
		{
			fieldname: "employee",
			label: __("员工"),
			fieldtype: "Link",
			options: "Employee"
		}
	],
	
	// 颜色含义：
	// 总工时：绿色 = ≥160小时（满勤），红色 = <80小时（低工时），黑色 = 正常
	// 迟到次数：橙色 = >3次
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname === "total_working_hours" && data) {
			if (data.total_working_hours >= 160) {
				// 绿色：满勤（≥160小时）
				value = `<span style="color: green; font-weight: bold">${value}</span>`;
			} else if (data.total_working_hours < 80) {
				// 红色：低工时（<80小时）
				value = `<span style="color: red">${value}</span>`;
			}
			// 黑色：正常（80-160小时之间）
		}
		
		if (column.fieldname === "late_entries" && data && data.late_entries > 3) {
			// 橙色：迟到次数超过3次
			value = `<span style="color: orange">${value}</span>`;
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

