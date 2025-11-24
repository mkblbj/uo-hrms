# -*- coding: utf-8 -*-
"""
创建测试打卡地点的辅助脚本

使用方法:
bench --site hrms.localhost execute hrms.hr.doctype.qr_checkin_location.create_test_location.create_test_locations
"""

import frappe
import secrets


def create_test_locations():
	"""创建测试打卡地点"""
	locations = [
		{
			"location_name": "office-10F",
			"description": "10楼办公室打卡点",
		},
	]
	
	created = []
	
	for loc in locations:
		if frappe.db.exists("QR Checkin Location", loc["location_name"]):
			print(f"地点 {loc['location_name']} 已存在，跳过")
			continue
		
		try:
			# 生成随机密钥
			secret = secrets.token_hex(32)
			
			doc = frappe.get_doc({
				"doctype": "QR Checkin Location",
				"location_name": loc["location_name"],
				"description": loc["description"],
				"secret": secret,
				"enabled": 1,
				"qr_refresh_interval": 30
			})
			doc.insert()
			frappe.db.commit()
			
			created.append(loc["location_name"])
			print(f"✓ 成功创建地点: {loc['location_name']}")
			
		except Exception as e:
			print(f"✗ 创建地点 {loc['location_name']} 失败: {str(e)}")
			frappe.db.rollback()
	
	if created:
		print(f"\n总共创建了 {len(created)} 个打卡地点:")
		for name in created:
			print(f"  - {name}")
	else:
		print("\n没有创建新的打卡地点")
	
	return created


def get_location_info(location_name):
	"""获取地点信息（不显示密钥）"""
	if not frappe.db.exists("QR Checkin Location", location_name):
		print(f"地点 {location_name} 不存在")
		return None
	
	doc = frappe.get_doc("QR Checkin Location", location_name)
	
	info = {
		"location_name": doc.location_name,
		"description": doc.description,
		"enabled": doc.enabled,
		"qr_refresh_interval": doc.qr_refresh_interval,
		"shift_location": doc.shift_location,
		"qr_display_url": f"/qr_display?location={doc.location_name}"
	}
	
	print(f"\n打卡地点信息: {location_name}")
	print("-" * 50)
	for key, value in info.items():
		print(f"{key:20s}: {value}")
	print("-" * 50)
	
	return info

