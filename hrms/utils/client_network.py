"""真实客户端地址与公司网络判断。

Frappe 的 request_ip 取的是 X-Forwarded-For 的第一个值，客户端可以自己填写。
经 Cloudflare 隧道进入时，CF-Connecting-IP 由 Cloudflare 写入，客户端伪造不了。
前提：源站端口不对公网开放，外部流量只经 Cloudflare 进入。
"""

import ipaddress

import frappe

OFFICE_NETWORKS_FIELD = "qr_checkin_allowed_ips"
CLOUDFLARE_CLIENT_IP_HEADER = "CF-Connecting-IP"


def get_client_ip() -> str | None:
	request = getattr(frappe.local, "request", None)
	headers = getattr(request, "headers", None) or {}
	cloudflare_ip = (headers.get(CLOUDFLARE_CLIENT_IP_HEADER) or "").strip()
	if cloudflare_ip and _parse_ip(cloudflare_ip) is not None:
		return cloudflare_ip
	return getattr(frappe.local, "request_ip", None)


def _network_lines(text: str | None) -> list[str]:
	lines = []
	for raw_line in (text or "").splitlines():
		line = raw_line.strip()
		if line and not line.startswith("#"):
			lines.append(line)
	return lines


def parse_network_list(text: str | None) -> list:
	networks = []
	for line in _network_lines(text):
		try:
			networks.append(ipaddress.ip_network(line, strict=False))
		except ValueError:
			continue
	return networks


def find_invalid_network_lines(text: str | None) -> list[str]:
	invalid = []
	for line in _network_lines(text):
		try:
			ipaddress.ip_network(line, strict=False)
		except ValueError:
			invalid.append(line)
	return invalid


def is_office_network(ip: str | None, networks_text: str | None = None) -> bool:
	address = _parse_ip(ip)
	if address is None:
		return False
	if networks_text is None:
		networks_text = frappe.db.get_single_value("HR Settings", OFFICE_NETWORKS_FIELD)
	return any(
		address.version == network.version and address in network
		for network in parse_network_list(networks_text)
	)


def _parse_ip(value):
	try:
		address = ipaddress.ip_address((value or "").strip())
	except ValueError:
		return None
	if address.version == 6 and address.ipv4_mapped:
		return address.ipv4_mapped
	return address
