# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

"""
NFC Checkin Page Controller
路由: /nfc-checkin 或 /nfc-checkin?loc=xxx
"""

import frappe

no_cache = 1

def get_context(context):
    """设置页面上下文"""
    # 设置 HTTP 响应头禁止缓存
    frappe.local.response["headers"] = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    
    # 获取地点参数
    location = frappe.form_dict.get("loc") or frappe.form_dict.get("location") or "unknown"
    
    context.location = location
    context.title = f"NFC 打卡 - {location}"
    context.no_cache = 1
    
    return context
