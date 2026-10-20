// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("PWA Notification", {
	onload(frm) {
		// 在后台手工发的通知默认算公司通知；代码发的各自写明类型
		if (frm.is_new() && frm.doc.notification_type === "Other") {
			frm.set_value("notification_type", "Announcement");
		}
	},
});
