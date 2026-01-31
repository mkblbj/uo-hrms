# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

"""
WebAuthn/Passkey API for NFC Check-in
支持 FaceID/TouchID/指纹 验证的 NFC 打卡
"""

import json
import base64
import secrets
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import now, now_datetime, get_datetime

# WebAuthn 配置
RP_ID = "erphr.toiroworld.com"
RP_NAME = "UO HR System"
ORIGIN = "https://erphr.toiroworld.com"

# Challenge 有效期（秒）
CHALLENGE_TIMEOUT = 300


def _generate_challenge() -> bytes:
    """生成随机 challenge"""
    return secrets.token_bytes(32)


def _b64_encode(data: bytes) -> str:
    """URL-safe base64 编码"""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64_decode(data: str) -> bytes:
    """URL-safe base64 解码"""
    # 补齐 padding
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


@frappe.whitelist()
def register_options():
    """
    步骤1: 获取 Passkey 注册选项
    员工在 HR 系统中注册 Passkey 时调用
    
    Returns:
        WebAuthn registration options (JSON)
    """
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        frappe.throw(_("Please login first"))
    
    # 获取员工信息
    employee = frappe.db.get_value(
        "Employee", 
        {"user_id": user}, 
        ["name", "employee_name"], 
        as_dict=True
    )
    if not employee:
        frappe.throw(_("Your account is not linked to an employee profile"))
    
    # 检查是否已有 Passkey（目前只支持单设备）
    existing = frappe.db.exists("Passkey Credential", {"user": user})
    if existing:
        frappe.throw(_("You already have a Passkey registered. Please delete it first before registering a new one."))
    
    # 生成 challenge
    challenge = _generate_challenge()
    challenge_b64 = _b64_encode(challenge)
    
    # 保存 challenge 到缓存
    frappe.cache().set_value(
        f"passkey_reg_challenge:{user}", 
        challenge_b64, 
        expires_in_sec=CHALLENGE_TIMEOUT
    )
    
    # 构建注册选项（符合 WebAuthn 规范）
    options = {
        "challenge": challenge_b64,
        "rp": {
            "name": RP_NAME,
            "id": RP_ID
        },
        "user": {
            "id": _b64_encode(user.encode()),
            "name": user,
            "displayName": employee.employee_name
        },
        "pubKeyCredParams": [
            {"alg": -7, "type": "public-key"},   # ES256
            {"alg": -257, "type": "public-key"}  # RS256
        ],
        "timeout": CHALLENGE_TIMEOUT * 1000,
        "authenticatorSelection": {
            "authenticatorAttachment": "platform",  # 使用设备内置认证器
            "residentKey": "preferred",
            "userVerification": "required"  # 必须验证用户（FaceID/指纹）
        },
        "attestation": "none"  # 不需要证明
    }
    
    return options


@frappe.whitelist()
def register_complete(credential: str, device_name: str = None):
    """
    步骤2: 完成 Passkey 注册
    
    Args:
        credential: 前端返回的 credential JSON 字符串
        device_name: 设备名称（可选）
    
    Returns:
        {"status": "ok", "message": "Passkey registered successfully"}
    """
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        frappe.throw(_("Please login first"))
    
    # 获取保存的 challenge
    challenge_b64 = frappe.cache().get_value(f"passkey_reg_challenge:{user}")
    if not challenge_b64:
        frappe.throw(_("Registration timeout, please try again"))
    
    # 清除 challenge（一次性使用）
    frappe.cache().delete_value(f"passkey_reg_challenge:{user}")
    
    try:
        cred_data = json.loads(credential)
    except json.JSONDecodeError:
        frappe.throw(_("Invalid credential format"))
    
    # 解析 clientDataJSON
    client_data_json = _b64_decode(cred_data["response"]["clientDataJSON"])
    client_data = json.loads(client_data_json)
    
    # 验证 challenge
    if client_data.get("challenge") != challenge_b64:
        frappe.throw(_("Challenge mismatch"))
    
    # 验证 origin
    if client_data.get("origin") != ORIGIN:
        frappe.throw(_("Origin mismatch"))
    
    # 验证 type
    if client_data.get("type") != "webauthn.create":
        frappe.throw(_("Invalid operation type"))
    
    # 获取 credential ID 和公钥
    credential_id = cred_data["id"]
    
    # attestationObject 包含公钥，这里简化处理
    # 实际生产环境应该使用 py_webauthn 库完整解析
    attestation_object = cred_data["response"]["attestationObject"]
    
    # 获取员工
    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    # 保存 credential
    doc = frappe.get_doc({
        "doctype": "Passkey Credential",
        "user": user,
        "employee": employee,
        "credential_id": credential_id,
        "public_key": attestation_object,  # 存储完整的 attestationObject
        "sign_count": 0,
        "device_name": device_name or _get_device_name_from_request(),
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return {"status": "ok", "message": _("Passkey registered successfully")}


@frappe.whitelist(allow_guest=True, methods=['POST', 'GET'])
def auth_options(location: str = None):
    """
    步骤3: 获取 Passkey 验证选项（NFC 打卡时调用）
    
    Args:
        location: 打卡地点（可选，用于日志）
    
    Returns:
        WebAuthn authentication options (JSON)
    """
    # 生成 challenge
    challenge = _generate_challenge()
    challenge_b64 = _b64_encode(challenge)
    
    # 保存 challenge 到缓存（用 challenge 本身作为 key，因为此时可能未登录）
    frappe.cache().set_value(
        f"passkey_auth_challenge:{challenge_b64}", 
        json.dumps({"location": location, "created": str(now())}),
        expires_in_sec=CHALLENGE_TIMEOUT
    )
    
    # 构建验证选项
    options = {
        "challenge": challenge_b64,
        "rpId": RP_ID,
        "timeout": CHALLENGE_TIMEOUT * 1000,
        "userVerification": "required",
        # 不指定 allowCredentials，允许任何已注册的 Passkey
    }
    
    return options


@frappe.whitelist(allow_guest=True, methods=['POST'])
def passkey_checkin(credential: str, location: str, latitude: float = None, longitude: float = None):
    """
    步骤4: 使用 Passkey 验证并打卡
    
    Args:
        credential: 前端返回的 credential JSON 字符串
        location: 打卡地点
    
    Returns:
        {
            "status": "ok",
            "log_type": "IN",
            "employee_name": "张三",
            "time": "2025-01-30 09:00:00",
            "location": "office-2f-door"
        }
    """
    try:
        cred_data = json.loads(credential)
    except json.JSONDecodeError:
        frappe.throw(_("Invalid credential format"))
    
    # 获取 credential_id
    credential_id = cred_data.get("id")
    if not credential_id:
        frappe.throw(_("Missing credential ID"))
    
    # 查找对应的 Passkey Credential
    cred_doc = frappe.db.get_value(
        "Passkey Credential",
        {"credential_id": credential_id},
        ["name", "user", "employee", "public_key", "sign_count"],
        as_dict=True
    )
    
    if not cred_doc:
        frappe.throw(_("Passkey not found. Please register first."))
    
    # 解析 clientDataJSON
    client_data_json = _b64_decode(cred_data["response"]["clientDataJSON"])
    client_data = json.loads(client_data_json)
    
    # 获取 challenge
    challenge_b64 = client_data.get("challenge")
    
    # 验证 challenge 是否有效
    challenge_data = frappe.cache().get_value(f"passkey_auth_challenge:{challenge_b64}")
    if not challenge_data:
        frappe.throw(_("Authentication timeout or invalid challenge"))
    
    # 清除 challenge（一次性使用）
    frappe.cache().delete_value(f"passkey_auth_challenge:{challenge_b64}")
    
    # 验证 origin
    if client_data.get("origin") != ORIGIN:
        frappe.throw(_("Origin mismatch"))
    
    # 验证 type
    if client_data.get("type") != "webauthn.get":
        frappe.throw(_("Invalid operation type"))
    
    # 解析 authenticatorData 获取 sign_count
    authenticator_data = _b64_decode(cred_data["response"]["authenticatorData"])
    # sign_count 在 authenticatorData 的第 33-36 字节（大端序）
    new_sign_count = int.from_bytes(authenticator_data[33:37], "big")
    
    # 验证 sign_count（防重放攻击）
    if new_sign_count <= cred_doc.sign_count:
        # 警告但不阻止（某些设备 sign_count 可能不递增）
        frappe.log_error(
            message=f"Sign count not incremented for user {cred_doc.user}. Old: {cred_doc.sign_count}, New: {new_sign_count}",
            title="Passkey Sign Count Warning"
        )
    
    # 更新 sign_count 和 last_used
    frappe.db.set_value("Passkey Credential", cred_doc.name, {
        "sign_count": new_sign_count,
        "last_used": now()
    })
    
    # ===== 以下是打卡逻辑 =====
    employee = cred_doc.employee
    
    # 获取上次打卡记录，用于自动判断 IN/OUT
    last_checkin = frappe.db.get_value(
        "Employee Checkin",
        {"employee": employee},
        ["log_type", "time"],
        order_by="time desc"
    )
    
    # 自动判断 IN/OUT
    if last_checkin:
        last_type, last_time = last_checkin
        # 如果今天有打卡记录
        if get_datetime(last_time).date() == now_datetime().date():
            log_type = "OUT" if last_type == "IN" else "IN"
        else:
            # 新的一天，从 IN 开始
            log_type = "IN"
    else:
        log_type = "IN"
    
    # 防重复打卡检查（5分钟内）
    recent_checkin = frappe.db.get_all(
        "Employee Checkin",
        filters={
            "employee": employee,
            "time": (">", now_datetime() - timedelta(minutes=5))
        },
        limit=1
    )
    
    if recent_checkin:
        frappe.throw(_("You have already checked in within the last 5 minutes"))
    
    # 创建 Employee Checkin
    checkin_data = {
        "doctype": "Employee Checkin",
        "employee": employee,
        "time": now(),
        "log_type": log_type,
        "device_id": f"NFC-Passkey:{location}",
        "skip_auto_attendance": 0,
    }
    
    # 如果提供了地理位置，设置经纬度
    if latitude is not None and longitude is not None:
        checkin_data["latitude"] = latitude
        checkin_data["longitude"] = longitude
    
    checkin = frappe.get_doc(checkin_data)
    checkin.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # 获取员工姓名
    employee_name = checkin.employee_name
    
    # 记录审计日志
    try:
        client_ip = frappe.local.request_ip or "Unknown"
        frappe.log_error(
            message=f"NFC-Passkey Checkin: Employee {employee} ({employee_name}) {log_type} at {location}. IP: {client_ip}",
            title=f"NFC-Passkey Checkin - {log_type}"
        )
    except Exception:
        pass
    
    action = _("Check-in") if log_type == "IN" else _("Check-out")
    return {
        "status": "ok",
        "message": _("{0} successful").format(action),
        "log_type": log_type,
        "employee": employee,
        "employee_name": employee_name,
        "time": str(checkin.time),
        "location": location
    }


@frappe.whitelist()
def get_my_passkeys():
    """
    获取当前用户的 Passkey 列表
    
    Returns:
        [{"name": "xxx", "device_name": "iPhone 15", "created_at": "...", "last_used": "..."}]
    """
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        return []
    
    passkeys = frappe.get_all(
        "Passkey Credential",
        filters={"user": user},
        fields=["name", "device_name", "created_at", "last_used"],
        order_by="created_at desc"
    )
    
    return passkeys


@frappe.whitelist()
def delete_passkey(passkey_name: str):
    """
    删除指定的 Passkey（只能删除自己的）
    
    Args:
        passkey_name: Passkey Credential 文档名称
    
    Returns:
        {"status": "ok", "message": "Passkey deleted"}
    """
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        frappe.throw(_("Permission denied"))
    
    # 验证是否是自己的 Passkey
    passkey_user = frappe.db.get_value("Passkey Credential", passkey_name, "user")
    if passkey_user != user:
        frappe.throw(_("You can only delete your own Passkey"))
    
    frappe.delete_doc("Passkey Credential", passkey_name, ignore_permissions=True)
    frappe.db.commit()
    
    return {"status": "ok", "message": _("Passkey deleted")}


@frappe.whitelist()
def check_passkey_registered():
    """
    检查当前用户是否已注册 Passkey
    
    Returns:
        {"registered": True/False, "device_name": "..."}
    """
    user = frappe.session.user
    if user in ("Guest", "Administrator"):
        return {"registered": False}
    
    passkey = frappe.db.get_value(
        "Passkey Credential",
        {"user": user},
        ["device_name", "created_at"],
        as_dict=True
    )
    
    if passkey:
        return {
            "registered": True,
            "device_name": passkey.device_name,
            "created_at": str(passkey.created_at)
        }
    
    return {"registered": False}


def _get_device_name_from_request() -> str:
    """从请求 User-Agent 推断设备名称"""
    try:
        ua = frappe.local.request.headers.get("User-Agent", "")
        
        if "iPhone" in ua:
            return "iPhone"
        elif "iPad" in ua:
            return "iPad"
        elif "Android" in ua:
            if "Samsung" in ua:
                return "Samsung"
            elif "Pixel" in ua:
                return "Google Pixel"
            elif "Xiaomi" in ua or "Mi " in ua:
                return "Xiaomi"
            elif "HUAWEI" in ua:
                return "Huawei"
            return "Android Device"
        elif "Mac" in ua:
            return "Mac"
        elif "Windows" in ua:
            return "Windows PC"
        
        return "Unknown Device"
    except Exception:
        return "Unknown Device"
