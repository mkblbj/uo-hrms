import { ref, watch } from "vue"

export const THEME_STORAGE_KEY = "hrms_theme_preference"

const VALID_THEMES = new Set(["light", "dark"])

export function resolveTheme({ osPrefersDark, stored }) {
	if (typeof stored === "string" && VALID_THEMES.has(stored)) return stored
	return osPrefersDark ? "dark" : "light"
}

function getOsPrefersDark() {
	if (typeof window === "undefined") return false
	return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false
}

function readStored() {
	try {
		return localStorage.getItem(THEME_STORAGE_KEY)
	} catch {
		return null
	}
}

function writeStored(value) {
	try {
		if (value === null) localStorage.removeItem(THEME_STORAGE_KEY)
		else localStorage.setItem(THEME_STORAGE_KEY, value)
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

	function resolve() {
		const resolved = resolveTheme({
			osPrefersDark: getOsPrefersDark(),
			stored: readStored(),
		})
		theme.value = resolved
		isDark.value = resolved === "dark"
	}

	function toggle() {
		const next = isDark.value ? "light" : "dark"
		writeStored(next)
		theme.value = next
		isDark.value = next === "dark"
	}

	function followSystem() {
		writeStored(null)
		resolve()
	}

	resolve()

	watch(theme, (value) => applyAttribute(value), { immediate: true })

	if (typeof window !== "undefined") {
		const mql = window.matchMedia("(prefers-color-scheme: dark)")
		mql.addEventListener("change", () => {
			if (readStored() === null) resolve()
		})
	}

	singleton = { isDark, theme, toggle, followSystem }
	return singleton
}
