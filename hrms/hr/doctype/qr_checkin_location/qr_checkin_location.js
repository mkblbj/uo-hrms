// Copyright (c) 2025, 株式会社UO and contributors
// For license information, please see license.txt

frappe.ui.form.on("QR Checkin Location", {
	refresh: function (frm) {
		// 添加生成密钥按钮
		if (frm.doc.__islocal) {
			frm.add_custom_button(__("Generate Secret Key"), function () {
				// 生成随机密钥
				const randomKey = Array.from(crypto.getRandomValues(new Uint8Array(32)))
					.map((b) => b.toString(16).padStart(2, "0"))
					.join("");
				frm.set_value("secret", randomKey);
				frappe.show_alert({
					message: __("Secret key generated successfully"),
					indicator: "green",
				});
			});
		}

		// 查看二维码页面、复制墙上屏网址（网址里带展示密钥）
		if (!frm.doc.__islocal && frm.doc.enabled) {
			const withDisplayUrl = (callback) =>
				frappe.call({
					method: "hrms.hr.doctype.qr_checkin_location.qr_checkin_location.get_display_url",
					args: { location_name: frm.doc.name },
					callback: (r) => r.message && callback(r.message),
				});
			frm.add_custom_button(
				__("View QR Code Page"),
				() => withDisplayUrl((url) => window.open(url, "_blank")),
				__("Actions"),
			);
			frm.add_custom_button(
				__("Copy Wall Display URL"),
				() =>
					withDisplayUrl((url) => {
						frappe.utils.copy_to_clipboard(url);
						frappe.show_alert({ message: __("Wall display URL copied"), indicator: "green" });
					}),
				__("Actions"),
			);
		}
	},
});
