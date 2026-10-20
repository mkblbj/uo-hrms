"""给原生 App 发 APNs 推送（HTTP/2 + 令牌认证）。

站点配置 site_config.json 里放 "uohr_apns": {"team_id", "key_id", "key_path"}；.p8 密钥不进任何仓库。
没配置时什么都不做。网页推送（PWA）不经过这里，照旧由 PWA Notification 自己发。
日志里不写设备令牌和通知正文。
"""

import json
import time
import traceback

import frappe

from hrms.utils.mobile_notifications import (
	DEFAULT_TITLES,
	DOCTYPE,
	FIELDS,
	display_html,
	plain_text,
	push_allowed,
	target,
	type_key,
	unread_count,
)

CONFIG_KEY = "uohr_apns"
DEVICE_DOCTYPE = "Mobile App Device"
HOSTS = {"production": "https://api.push.apple.com", "sandbox": "https://api.sandbox.push.apple.com"}
PAYLOAD_VERSION = 1
BODY_LIMIT = 178
EXPIRATION_SECONDS = 24 * 3600
# 苹果要求令牌不超过 1 小时、也不能换得太勤
TOKEN_TTL_SECONDS = 40 * 60
RETRY_DELAY_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 10
REMOVE_DEVICE_REASONS = {"BadDeviceToken", "DeviceTokenNotForTopic"}
PROVIDER_TOKEN_REASONS = {"InvalidProviderToken", "ExpiredProviderToken"}


def get_config() -> dict | None:
	config = frappe.conf.get(CONFIG_KEY)
	if not isinstance(config, dict) or not all(config.get(key) for key in ("team_id", "key_id", "key_path")):
		return None
	return config


def queue_push(notification) -> None:
	"""PWA Notification 发推送时调用：配了 APNs、本人登记过设备，就在事务提交后交给后台队列。"""
	if not get_config() or not notification.to_user:
		return
	if not frappe.db.exists(DEVICE_DOCTYPE, {"user": notification.to_user}):
		return
	frappe.enqueue(
		"hrms.utils.apns.send_notification",
		queue="short",
		enqueue_after_commit=True,
		notification=str(notification.name),
	)


def build_payload(row, badge: int) -> dict:
	kind = type_key(row.notification_type)
	return {
		"aps": {
			"alert": {
				"title": row.notification_title or DEFAULT_TITLES[kind],
				"body": plain_text(display_html(row), BODY_LIMIT),
			},
			"sound": "default",
			"badge": badge,
			"thread-id": kind,
		},
		"uohr": {
			"v": PAYLOAD_VERSION,
			"notification": str(row.name),
			"type": kind,
			"target": target(row, row.to_user),
		},
	}


def payload_for(notification: str) -> dict | None:
	"""这条通知现在该推给本人的载荷；不该推（停用、关了开关）时 None。"""
	prepared = _prepare(notification)
	return prepared[1] if prepared else None


def _prepare(notification: str) -> tuple[str, dict] | None:
	row = frappe.db.get_value(DOCTYPE, notification, FIELDS, as_dict=True)
	if not row or not row.to_user:
		return None
	if not frappe.db.get_value("User", row.to_user, "enabled"):
		return None
	if not push_allowed(row.to_user, type_key(row.notification_type)):
		return None
	return row.to_user, build_payload(row, unread_count(row.to_user))


def _devices(user: str, names: list[str] | None = None) -> list:
	# 按收件人过滤：设备可能已经换到别的账号（同一部手机换账号登录）
	filters = {"user": user}
	if names is not None:
		filters["name"] = ["in", names]
	return frappe.get_all(DEVICE_DOCTYPE, filters=filters, fields=["name", "device_token", "environment", "bundle_id"])


def _log_job_failure(notification: str, error: Exception) -> None:
	"""只记代码位置和异常类型：异常文字和局部变量里可能有设备令牌。"""
	frames = "".join(traceback.format_tb(error.__traceback__))
	frappe.log_error("APNs push job failed", f"Notification {notification}: {type(error).__name__}\n{frames}")


def send_notification(notification: str) -> None:
	try:
		_send_notification(notification)
	except Exception as error:
		_log_job_failure(notification, error)


def _send_notification(notification: str) -> None:
	config = get_config()
	prepared = _prepare(notification) if config else None
	if not prepared:
		return
	user, payload = prepared
	_deliver(config, notification, payload, _devices(user), retry=True)


def retry_notification(notification: str, devices: list[str], not_before: float) -> None:
	"""429 / 5xx / 网络错误之后再发一次。同一批失败一起入队：第一个任务等到时间，后面的到点就不用再等。"""
	try:
		_retry_notification(notification, devices, not_before)
	except Exception as error:
		_log_job_failure(notification, error)


def _retry_notification(notification: str, devices: list[str], not_before: float) -> None:
	wait = not_before - time.time()
	if wait > 0:
		time.sleep(min(wait, RETRY_DELAY_SECONDS))
	config = get_config()
	prepared = _prepare(notification) if config else None
	if not prepared:
		return
	user, payload = prepared
	_deliver(config, notification, payload, _devices(user, devices), retry=False)


def _deliver(config: dict, notification: str, payload: dict, devices: list, retry: bool) -> None:
	if not devices:
		return
	import httpx

	body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
	failed = []
	with httpx.Client(http2=True, timeout=REQUEST_TIMEOUT_SECONDS) as client:
		for device in devices:
			status, reason = _post(client, config, notification, device, body)
			if status is None:
				# 密钥读不了：已记日志，这一轮都不用再试
				return
			if _handle_response(config, notification, device, status, reason):
				failed.append(device.name)
	if not failed:
		return
	if retry:
		frappe.enqueue(
			"hrms.utils.apns.retry_notification",
			queue="short",
			notification=notification,
			devices=failed,
			not_before=time.time() + RETRY_DELAY_SECONDS,
		)
	else:
		frappe.log_error(
			"APNs push failed after retry",
			f"Notification {notification}: devices {', '.join(failed)} still failing.",
		)


def _post(client, config: dict, notification: str, device, body: bytes) -> tuple[int | None, str | None]:
	"""返回 (HTTP 状态, 苹果的 reason)；网络错误当作 503。"""
	import httpx

	token = provider_token(config)
	if not token:
		return None, None
	headers = {
		"authorization": f"bearer {token}",
		"apns-topic": device.bundle_id,
		"apns-push-type": "alert",
		"apns-priority": "10",
		"apns-expiration": str(int(time.time()) + EXPIRATION_SECONDS),
		"apns-collapse-id": notification,
	}
	url = f"{HOSTS.get(device.environment, HOSTS['production'])}/3/device/{device.device_token}"
	try:
		response = client.post(url, headers=headers, content=body)
	except httpx.HTTPError as error:
		return 503, type(error).__name__
	reason = None
	if response.content:
		try:
			reason = response.json().get("reason")
		except ValueError:
			reason = None
	return response.status_code, reason


def _handle_response(config: dict, notification: str, device, status: int, reason: str | None) -> bool:
	"""处理苹果的回应；返回 True 表示值得过一会儿再试。"""
	if status == 200:
		return False
	if status == 410 or (status == 400 and reason in REMOVE_DEVICE_REASONS):
		# 卸载了 App、令牌失效或不属于这个 App：这台设备不用再推
		frappe.db.delete(DEVICE_DOCTYPE, {"name": device.name})
		return False
	if status == 429 or status >= 500:
		return True
	if status == 403 and reason in PROVIDER_TOKEN_REASONS:
		frappe.cache.delete_value(_token_cache_key(config))
	frappe.log_error(
		"APNs push rejected",
		f"Notification {notification}, device {device.name}: HTTP {status} {reason or ''}".strip(),
	)
	return False


def _token_cache_key(config: dict) -> str:
	return f"uohr_apns_provider_token:{config['team_id']}:{config['key_id']}"


def provider_token(config: dict) -> str | None:
	"""ES256 签名的 JWT，缓存 40 分钟。密钥读不了时记日志、返回 None。"""
	key = _token_cache_key(config)
	token = frappe.cache.get_value(key)
	if token:
		return token
	import jwt

	try:
		with open(config["key_path"], "rb") as file:
			private_key = file.read()
		token = jwt.encode(
			{"iss": config["team_id"], "iat": int(time.time())},
			private_key,
			algorithm="ES256",
			headers={"kid": config["key_id"], "typ": None},
		)
	except Exception:
		frappe.log_error("APNs key could not be used", f"Check {CONFIG_KEY} in site_config.json.")
		return None
	frappe.cache.set_value(key, token, expires_in_sec=TOKEN_TTL_SECONDS)
	return token
