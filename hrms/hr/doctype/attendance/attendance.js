// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Attendance", {
	refresh(frm) {
		if (frm.doc.__islocal && !frm.doc.attendance_date) {
			frm.set_value("attendance_date", frappe.datetime.get_today());
		}

		frm.set_query("employee", () => {
			return {
				query: "erpnext.controllers.queries.employee_query",
			};
		});

		if (frm.doc.docstatus === 1 && frm.doc.status === "Absent") {
			frm.add_custom_button(
				__("Attendance Request"),
				() => {
					frappe.new_doc("Attendance Request", {
						employee: frm.doc.employee,
						from_date: frm.doc.attendance_date,
						to_date: frm.doc.attendance_date,
					});
				},
				__("Create"),
			);
		}

		// Add recalculate attendance button
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(
				__("Recalculate"),
				() => {
					frappe.confirm(
						__("This will cancel this attendance and recalculate based on checkin records. Continue?"),
						function() {
							frappe.call({
								method: "hrms.hr.doctype.employee_checkin.employee_checkin_utils.recalculate_attendance",
								args: {
									employee: frm.doc.employee,
									date: frm.doc.attendance_date
								},
								freeze: true,
								freeze_message: __("Recalculating Attendance..."),
								callback: function(r) {
									if (r.message) {
										if (r.message.status === "success") {
											frappe.show_alert({
												message: __("Attendance recalculated: {0} hours, Status: {1}", [
													r.message.working_hours,
													r.message.attendance_status
												]),
												indicator: "green"
											});
											// Navigate to new attendance
											frappe.set_route("Form", "Attendance", r.message.attendance);
										} else {
											frappe.show_alert({
												message: r.message.message,
												indicator: r.message.status === "warning" ? "orange" : "red"
											});
											frm.reload_doc();
										}
									}
								}
							});
						}
					);
				},
				__("Actions"),
			);
		}
	},
});
