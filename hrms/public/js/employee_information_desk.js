$(document)
	.off("desktop_screen.employee_information_overview")
	.on("desktop_screen.employee_information_overview", (_event, { desktop }) => {
		if (
			!frappe.user.has_role(["HR User", "HR Manager", "System Manager"]) ||
			!frappe.model.can_get_report("Employee")
		) {
			return;
		}

		const grid = desktop.wrapper.find(".icons");
		if (grid.find("[data-employee-information-overview]").length) return;
		const icon = $(
			frappe.render_template("desktop_icon", {
				icon: {
					label: "Employee Information Overview",
					logo_url: "/assets/hrms/icons/desktop_icons/hr_setup.svg",
				},
			})
		);
		icon.attr({
			href: "/desk/query-report/Employee%20Information%20Overview",
			"data-employee-information-overview": "1",
		});
		grid.append(icon);
		icon.find('[data-toggle="tooltip"]').tooltip({ placement: "bottom" });
	});
