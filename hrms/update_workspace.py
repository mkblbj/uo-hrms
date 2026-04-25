import frappe
import json

def execute():
    """Update the Shift & Attendance workspace with new reports"""
    workspace_path = "/workspace/frappe-bench/apps/hrms/hrms/hr/workspace/shift_&_attendance/shift_&_attendance.json"
    
    with open(workspace_path, "r") as f:
        ws_data = json.load(f)
    
    ws_name = ws_data.get("name")
    
    if not frappe.db.exists("Workspace", ws_name):
        print(f"Workspace '{ws_name}' not found")
        return
    
    ws = frappe.get_doc("Workspace", ws_name)
    
    # Update the links
    ws.links = []
    for link in ws_data.get("links", []):
        ws.append("links", link)
    
    # Update shortcuts
    ws.shortcuts = []
    for sc in ws_data.get("shortcuts", []):
        ws.append("shortcuts", sc)
    
    ws.save(ignore_permissions=True)
    frappe.db.commit()
    
    print(f"Updated workspace: {ws_name}")
    print(f"Links count: {len(ws.links)}")
    print(f"Shortcuts count: {len(ws.shortcuts)}")

