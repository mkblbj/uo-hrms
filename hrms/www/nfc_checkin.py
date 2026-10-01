# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

"""NFC 打卡已停用。墙上的 NFC 贴片还指向这里，只显示停用提示，不再调用任何打卡接口。"""

no_cache = 1


def get_context(context):
	context.no_cache = 1
	return context
