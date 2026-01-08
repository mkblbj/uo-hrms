"""
发送 PWA 公告通知给所有员工
"""
import frappe

def send_to_all_employees(message, from_user=None):
    """
    给所有活跃员工发送通知
    
    用法:
        bench --site hrms.localhost execute hrms.send_announcement.send_to_all_employees --args '["公告内容"]'
        
        # 或指定发送者
        bench --site hrms.localhost execute hrms.send_announcement.send_to_all_employees --args '["公告内容", "Administrator"]'
    """
    if not from_user:
        from_user = frappe.session.user or "Administrator"
    
    # 获取所有活跃员工的用户ID
    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active", "user_id": ["is", "set"]},
        fields=["user_id", "employee_name"]
    )
    
    print(f"准备发送通知给 {len(employees)} 个员工...")
    
    success_count = 0
    for emp in employees:
        try:
            notification = frappe.new_doc("PWA Notification")
            notification.from_user = from_user
            notification.to_user = emp.user_id
            notification.message = message
            notification.insert(ignore_permissions=True)
            success_count += 1
        except Exception as e:
            print(f"发送给 {emp.employee_name} 失败: {e}")
    
    frappe.db.commit()
    print(f"✅ 成功发送 {success_count}/{len(employees)} 条通知")


def send_to_user(user, message, from_user=None):
    """
    给单个用户发送通知
    
    用法:
        bench --site hrms.localhost execute hrms.send_announcement.send_to_user --args '["user@example.com", "消息内容"]'
    """
    if not from_user:
        from_user = frappe.session.user or "Administrator"
    
    notification = frappe.new_doc("PWA Notification")
    notification.from_user = from_user
    notification.to_user = user
    notification.message = message
    notification.insert(ignore_permissions=True)
    frappe.db.commit()
    
    print(f"✅ 已发送通知给 {user}")


def list_recent_notifications(limit=10):
    """查看最近的通知"""
    notifications = frappe.get_all(
        "PWA Notification",
        fields=["name", "to_user", "message", "read", "creation"],
        order_by="creation desc",
        limit=limit
    )
    
    print(f"最近 {len(notifications)} 条通知:")
    for n in notifications:
        status = "✓" if n.read else "○"
        print(f"  {status} {n.creation} -> {n.to_user}: {n.message[:50]}...")
