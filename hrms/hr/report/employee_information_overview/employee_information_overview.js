(() => {
	const escape = (value) => frappe.utils.escape_html(value == null ? "" : String(value));
	const contacts = new Set([
		"cell_number",
		"custom_wechat_id",
		"current_address",
		"emergency_phone_number",
	]);
	const editableFields = [
		{ fieldname: "cell_number", label: __("Mobile"), fieldtype: "Data", options: "Phone" },
		{ fieldname: "custom_wechat_id", label: __("WeChat ID"), fieldtype: "Data" },
		{ fieldname: "current_address", label: __("Current Address"), fieldtype: "Small Text" },
		{
			fieldname: "company_email",
			label: __("Company Email"),
			fieldtype: "Data",
			options: "Email",
		},
		{
			fieldname: "personal_email",
			label: __("Personal Email"),
			fieldtype: "Data",
			options: "Email",
		},
		{
			fieldname: "person_to_be_contacted",
			label: __("Emergency Contact Name"),
			fieldtype: "Data",
		},
		{ fieldname: "relation", label: __("Emergency Contact Relationship"), fieldtype: "Data" },
		{
			fieldname: "emergency_phone_number",
			label: __("Emergency Phone"),
			fieldtype: "Data",
			options: "Phone",
		},
	];
	const statusLabels = {
		Active: __("Employed"),
		Inactive: __("Inactive Employee"),
		Suspended: __("Suspended Employee"),
		Left: __("Former Employee"),
	};
	const settings = {
		filters: [
			{
				fieldname: "search",
				label: __("Search Employees"),
				fieldtype: "Data",
				description: __("Name, employee ID, employee number, mobile or WeChat ID"),
			},
			{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company" },
			{
				fieldname: "department",
				label: __("Department"),
				fieldtype: "Link",
				options: "Department",
			},
			{
				fieldname: "status",
				label: __("Status"),
				fieldtype: "Select",
				default: "Active",
				options: [
					"",
					...Object.entries(statusLabels).map(([value, label]) => ({ value, label })),
				],
			},
			{ fieldname: "missing_phone", label: __("Missing Mobile"), fieldtype: "Check" },
			{
				fieldname: "missing_address",
				label: __("Missing Current Address"),
				fieldtype: "Check",
			},
		],

		after_datatable_render(datatable) {
			const employeeId = datatable.datamanager
				.getColumns()
				.find((column) => column.id === "name");
			if (employeeId) {
				datatable.columnmanager.setColumnSticky(
					employeeId.colIndex,
					!window.matchMedia("(max-width: 767px)").matches
				);
			}
		},

		async quick_edit(report, employee) {
			const response = await frappe.call({
				method: "frappe.client.get",
				args: { doctype: "Employee", name: employee },
				freeze: true,
			});
			const doc = response.message;
			const accountEmail = doc.user_id && doc.user_id.includes("@") ? doc.user_id : "";
			const dialog = new frappe.ui.Dialog({
				title: __("Quick Edit Employee"),
				fields: [
					{
						fieldname: "employee_name",
						label: __("Employee Name"),
						fieldtype: "Data",
						read_only: 1,
						default: doc.employee_name,
					},
					...editableFields.flatMap((field) => {
						const input = { ...field, default: doc[field.fieldname] || "" };
						return field.fieldname === "person_to_be_contacted"
							? [
									{ fieldtype: "Section Break", label: __("Emergency Contact") },
									input,
							  ]
							: [input];
					}),
					{
						fieldname: "account_email",
						label: __("Account Email"),
						fieldtype: "Data",
						read_only: 1,
						default: accountEmail,
						description: __(
							"Account email is shown when both contact email fields are empty."
						),
					},
				],
				primary_action_label: __("Save"),
				async primary_action(values) {
					const updated = { ...doc };
					for (const field of editableFields)
						updated[field.fieldname] = values[field.fieldname] ?? "";
					await frappe.call({
						method: "frappe.client.save",
						args: { doc: JSON.stringify(updated) },
						freeze: true,
					});
					dialog.hide();
					frappe.show_alert({
						message: __("Employee information updated."),
						indicator: "green",
					});
					await report.refresh();
				},
			});
			dialog.show();
		},

		onload(report) {
			report.$report
				.off("click.employee_overview")
				.on(
					"click.employee_overview",
					"[data-contact-field], [data-edit-employee]",
					(event) => {
						event.preventDefault();
						event.stopPropagation();
						if (event.currentTarget.dataset.editEmployee) {
							return settings.quick_edit(
								report,
								event.currentTarget.dataset.editEmployee
							);
						}
						const { employee, contactField } = event.currentTarget.dataset;
						if (!contacts.has(contactField)) return;
						const row = report.data.find((item) => item.name === employee);
						if (!row) return;
						if (contactField === "current_address") {
							const dialog = new frappe.ui.Dialog({
								title: __("Current Address"),
								fields: [
									{
										fieldtype: "HTML",
										options: `<div style="white-space: pre-wrap; overflow-wrap: anywhere; padding: 12px 0">${escape(
											row.current_address
										)}</div>`,
									},
								],
								primary_action_label: __("Copy Address"),
								primary_action: () =>
									frappe.utils.copy_to_clipboard(row.current_address),
							});
							dialog.show();
						} else {
							frappe.utils.copy_to_clipboard(row[contactField]);
						}
					}
				);
		},

		formatter(value, row, column, data, default_formatter) {
			if (!data) return default_formatter(value, row, column, data);
			const field = column.fieldname;
			if (field === "employee_name" || field === "name") {
				const id = encodeURIComponent(data.name).replace(/'/g, "%27");
				const link = `<a href="/app/employee/${id}" style="min-width: 0; overflow: hidden; text-overflow: ellipsis">${escape(
					value
				)}</a>`;
				if (field === "employee_name" && frappe.model.can_write("Employee")) {
					return `<span style="display: flex; align-items: center; gap: 6px; justify-content: space-between">${link}<button type="button" class="btn btn-default btn-xs" data-edit-employee="${escape(
						data.name
					)}" title="${escape(__("Quick Edit"))}">${escape(__("Edit"))}</button></span>`;
				}
				return link;
			}
			if (contacts.has(field)) {
				if (value == null || !String(value).trim()) {
					return `<span class="text-muted">${
						field === "custom_wechat_id" ? "—" : escape(__("Not provided"))
					}</span>`;
				}
				const title =
					field === "current_address"
						? __("View and copy full address")
						: __("Copy to clipboard");
				return `<button type="button" class="btn btn-link p-0 text-left" style="max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; vertical-align: middle" data-contact-field="${field}" data-employee="${escape(
					data.name
				)}" title="${escape(title)}">${escape(value)}</button>`;
			}
			if (field === "status") return escape(statusLabels[value] || __(value));
			if (field === "date_of_joining" || column.fieldtype === "Link") {
				return default_formatter(value, row, column, data);
			}
			return escape(value);
		},
	};
	frappe.query_reports["Employee Information Overview"] = settings;
})();
