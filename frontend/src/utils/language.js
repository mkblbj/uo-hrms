export const PWA_LANGUAGE_STORAGE_KEY = "hrms:pwa_language"
export const PWA_LANGUAGE_RESET_STORAGE_KEY = "hrms:pwa_language_reset"
export const PWA_LANGUAGE_RESET_VERSION = "2026-06-06-ja"
export const PWA_LANGUAGE_OPTIONS = Object.freeze([
	{ value: "zh", shortLabel: "中", label: "中文" },
	{ value: "ja", shortLabel: "日", label: "日本語" },
	{ value: "en", shortLabel: "EN", label: "English" },
])

const PWA_LANGUAGE_RESET_TARGET = "ja"

const SUPPORTED_LANGUAGES = new Set(
	PWA_LANGUAGE_OPTIONS.map((option) => option.value)
)

export function normalizeLanguage(lang) {
	if (!lang || typeof lang !== "string") return null
	const normalized = lang.trim().replaceAll("_", "-").toLowerCase()
	if (!normalized) return null
	const base = normalized.split("-", 1)[0]
	return SUPPORTED_LANGUAGES.has(base) ? base : null
}

export function getStoredLanguage(storage = globalThis?.localStorage) {
	const normalized = normalizeLanguage(storage?.getItem?.(PWA_LANGUAGE_STORAGE_KEY))
	if (!normalized && storage?.removeItem) {
		storage.removeItem(PWA_LANGUAGE_STORAGE_KEY)
	}
	return normalized
}

export function getServerLanguage(boot = globalThis.window?.frappe?.boot) {
	return normalizeLanguage(boot?.server_lang || boot?.lang) || "en"
}

export function resolveEffectiveLanguage({
	boot = globalThis.window?.frappe?.boot,
	storage = globalThis?.localStorage,
} = {}) {
	return getStoredLanguage(storage) || getServerLanguage(boot)
}

function resetPwaLanguageToJapaneseOnce(storage = globalThis?.localStorage) {
	try {
		if (storage?.getItem?.(PWA_LANGUAGE_RESET_STORAGE_KEY) === PWA_LANGUAGE_RESET_VERSION) {
			return false
		}

		storage?.setItem?.(PWA_LANGUAGE_STORAGE_KEY, PWA_LANGUAGE_RESET_TARGET)
		storage?.setItem?.(PWA_LANGUAGE_RESET_STORAGE_KEY, PWA_LANGUAGE_RESET_VERSION)
	} catch {
		return true
	}
	return true
}

export function initializeBootLanguage({
	boot = globalThis.window?.frappe?.boot,
	storage = globalThis?.localStorage,
} = {}) {
	const serverLang = normalizeLanguage(boot?.lang) || "en"
	const didResetLanguage = resetPwaLanguageToJapaneseOnce(storage)
	const effectiveLang = didResetLanguage
		? PWA_LANGUAGE_RESET_TARGET
		: getStoredLanguage(storage) || serverLang

	if (boot) {
		boot.server_lang = serverLang
		boot.lang = effectiveLang
	}

	return { serverLang, effectiveLang }
}

export function persistLanguage(lang, storage = globalThis?.localStorage) {
	const normalized = normalizeLanguage(lang)
	if (!normalized) {
		throw new Error(`Unsupported PWA language: ${lang}`)
	}
	storage?.setItem?.(PWA_LANGUAGE_STORAGE_KEY, normalized)
	return normalized
}

export function changeLanguage(
	lang,
	{
		boot = globalThis.window?.frappe?.boot,
		storage = globalThis?.localStorage,
		reload = () => globalThis.window?.location?.reload(),
	} = {},
) {
	const normalized = persistLanguage(lang, storage)
	if (boot) {
		boot.lang = normalized
	}
	reload()
	return normalized
}
