CHECKIN_COOLDOWN_EXEMPT_EMPLOYEES = frozenset({"44"})


def is_checkin_cooldown_exempt(employee: str | None) -> bool:
	return str(employee or "") in CHECKIN_COOLDOWN_EXEMPT_EMPLOYEES
