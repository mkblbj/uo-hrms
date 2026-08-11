import { ref, watch } from "vue"

export const THEME_OVERRIDE_KEY = "hrms_theme_override"
export const LEGACY_THEME_KEY = "hrms_theme_preference"

const LIGHT_HOUR = 8
const DARK_HOUR = 16
const VALID_THEMES = new Set(["light", "dark"])

function startOfHour(date, hour, dayOffset = 0) {
	const result = new Date(date)
	result.setDate(result.getDate() + dayOffset)
	result.setHours(hour, 0, 0, 0)
	return result
}

// The dark window runs from 16:00 to 08:00 the next morning, so the small hours
// belong to the window that opened the previous evening. Override expiry hangs
// entirely off getting this boundary right.
function windowStart(now) {
	const hour = now.getHours()
	if (hour >= LIGHT_HOUR && hour < DARK_HOUR) return startOfHour(now, LIGHT_HOUR)
	if (hour >= DARK_HOUR) return startOfHour(now, DARK_HOUR)
	return startOfHour(now, DARK_HOUR, -1)
}

function windowTheme(now) {
	const hour = now.getHours()
	return hour >= LIGHT_HOUR && hour < DARK_HOUR ? "light" : "dark"
}

export function getNextBoundary(now) {
	const hour = now.getHours()
	if (hour < LIGHT_HOUR) return startOfHour(now, LIGHT_HOUR)
	if (hour < DARK_HOUR) return startOfHour(now, DARK_HOUR)
	return startOfHour(now, LIGHT_HOUR, 1)
}

// setTimeout fires immediately on a zero or negative delay and would then
// re-arm in a tight loop, so the delay is floored to one second.
export function getBoundaryDelay(now) {
	return Math.max(1000, getNextBoundary(now).getTime() - now.getTime())
}

export function resolveTheme({ now, override }) {
	const fallback = windowTheme(now)
	if (!override || typeof override !== "object") return fallback
	if (!VALID_THEMES.has(override.theme)) return fallback
	if (!Number.isFinite(override.at)) return fallback
	if (override.at > now.getTime()) return fallback
	if (override.at < windowStart(now).getTime()) return fallback
	return override.theme
}

export function readOverride() {
	try {
		localStorage.removeItem(LEGACY_THEME_KEY)
		const raw = localStorage.getItem(THEME_OVERRIDE_KEY)
		if (!raw) return null
		const parsed = JSON.parse(raw)
		if (!parsed || typeof parsed !== "object") return null
		return { theme: parsed.theme, at: parsed.at }
	} catch {
		return null
	}
}

export function writeOverride(theme, at) {
	try {
		localStorage.setItem(THEME_OVERRIDE_KEY, JSON.stringify({ theme, at }))
	} catch {
		/* storage blocked */
	}
}

function applyAttribute(theme) {
	if (typeof document === "undefined") return
	document.documentElement.setAttribute("data-theme", theme)
}

let singleton = null

export function useTheme() {
	if (singleton) return singleton

	const isDark = ref(false)
	const theme = ref("light")
	let timer = null

	function apply(now = new Date()) {
		const resolved = resolveTheme({ now, override: readOverride() })
		theme.value = resolved
		isDark.value = resolved === "dark"
	}

	// One timeout aimed at the next boundary, re-armed each time it fires —
	// cheaper and more accurate than polling every minute.
	function schedule(now = new Date()) {
		if (typeof window === "undefined") return
		if (timer) clearTimeout(timer)
		timer = setTimeout(() => {
			const firedAt = new Date()
			apply(firedAt)
			schedule(firedAt)
		}, getBoundaryDelay(now))
	}

	function toggle() {
		const now = new Date()
		const next = isDark.value ? "light" : "dark"
		writeOverride(next, now.getTime())
		apply(now)
		schedule(now)
	}

	apply()
	schedule()

	watch(theme, (value) => applyAttribute(value), { immediate: true })

	// Mobile browsers throttle or freeze timers in the background, so a boundary
	// crossed while the page was hidden would otherwise be missed entirely.
	if (typeof document !== "undefined") {
		document.addEventListener("visibilitychange", () => {
			if (document.visibilityState !== "visible") return
			const now = new Date()
			apply(now)
			schedule(now)
		})
	}

	singleton = { isDark, theme, toggle }
	return singleton
}
