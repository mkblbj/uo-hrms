# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PasskeyCredential(Document):
    def before_insert(self):
        self.created_at = frappe.utils.now()
    
    def on_trash(self):
        # 删除时记录日志
        frappe.log_error(
            message=f"Passkey deleted for user {self.user}, employee {self.employee}, device: {self.device_name}",
            title="Passkey Credential Deleted"
        )
