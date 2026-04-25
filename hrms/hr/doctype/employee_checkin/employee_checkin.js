// Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Checkin", {
	refresh: async (frm) => {
		if (frm.doc.offshift) {
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				__(
					"This check-in is outside assigned shift hours and will not be considered for attendance. If a shift is assigned, adjust its time window and Fetch Shift again.",
				),
			);
		}
		if (!frm.doc.__islocal) {
			frm.trigger("add_fetch_shift_button");
			frm.trigger("add_recalculate_attendance_button");
		}

		const allow_geolocation_tracking = await frappe.db.get_single_value(
			"HR Settings",
			"allow_geolocation_tracking",
		);

		if (!allow_geolocation_tracking) {
			hide_field(["fetch_geolocation", "latitude", "longitude", "geolocation"]);
			return;
		}
	},

	fetch_geolocation: (frm) => {
		hrms.fetch_geolocation(frm);
	},

	add_fetch_shift_button(frm) {
		if (frm.doc.attendance) return;
		frm.add_custom_button(__("Fetch Shift"), function () {
			frappe.call({
				method: "fetch_shift",
				doc: frm.doc,
				freeze: true,
				freeze_message: __("Fetching Shift"),
				callback: function () {
					if (frm.doc.shift) {
						frappe.show_alert({
							message: __("Shift has been successfully updated to {0}.", [
								frm.doc.shift,
							]),
							indicator: "green",
						});
						frm.dirty();
						frm.save();
					} else {
						frappe.show_alert({
							message: __("No valid shift found for log time"),
							indicator: "orange",
						});
						frm.dirty();
						frm.save();
					}
				},
			});
		});
	},

	add_recalculate_attendance_button(frm) {
		// Add button to recalculate attendance for this date
		frm.add_custom_button(__("Recalculate Attendance"), function () {
			let checkin_date = frappe.datetime.str_to_obj(frm.doc.time).toISOString().split('T')[0];
			
			frappe.confirm(
				__("This will recalculate attendance for {0} on {1}. Continue?", [frm.doc.employee_name, checkin_date]),
				function() {
					frappe.call({
						method: "hrms.hr.doctype.employee_checkin.employee_checkin_utils.recalculate_attendance",
						args: {
							employee: frm.doc.employee,
							date: checkin_date
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
									frm.reload_doc();
								} else {
									frappe.show_alert({
										message: r.message.message,
										indicator: r.message.status === "warning" ? "orange" : "red"
									});
								}
							}
						}
					});
				}
			);
		}, __("Actions"));
	},
});
