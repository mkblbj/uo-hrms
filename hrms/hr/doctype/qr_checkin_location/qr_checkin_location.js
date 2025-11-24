// Copyright (c) 2025, 株式会社UO and contributors
// For license information, please see license.txt

frappe.ui.form.on('QR Checkin Location', {
	refresh: function(frm) {
		// 添加生成密钥按钮
		if (frm.doc.__islocal) {
			frm.add_custom_button(__('Generate Secret Key'), function() {
				// 生成随机密钥
				const randomKey = Array.from(crypto.getRandomValues(new Uint8Array(32)))
					.map(b => b.toString(16).padStart(2, '0'))
					.join('');
				frm.set_value('secret', randomKey);
				frappe.show_alert({
					message: __('Secret key generated successfully'),
					indicator: 'green'
				});
			});
		}
		
		// 添加查看二维码按钮
		if (!frm.doc.__islocal && frm.doc.enabled) {
			frm.add_custom_button(__('View QR Code Page'), function() {
				const url = `/qr_display?location=${encodeURIComponent(frm.doc.location_name)}`;
				window.open(url, '_blank');
			}, __('Actions'));
		}
	}
});

