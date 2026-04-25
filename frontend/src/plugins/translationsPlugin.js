function makeTranslationFunction() {
	let messages = {}
	return {
		translate,
		load: () => Promise.allSettled([setup()]),
	}

	async function setup() {
		const boot = window.frappe?.boot ?? {}
		const targetLang = boot.lang ?? navigator.language
		const serverLang = boot.server_lang ?? boot.lang ?? navigator.language

		if (shouldUseBootMessages(targetLang, serverLang, boot.__messages)) {
			messages = boot.__messages
			return
		}

		try {
			messages = await fetchTranslations({ lang: targetLang })
			boot.__messages = messages
		} catch (error) {
			console.error("Failed to fetch translations:", error)
			boot.lang = serverLang
			messages = boot.__messages || {}
		}
	}

	function translate(txt, replace, context = null) {
		if (!txt || typeof txt != "string") return txt

		let translated_text = ""
		let key = txt
		if (context) {
			translated_text = messages[`${key}:${context}`]
		}
		if (!translated_text) {
			translated_text = messages[key] || txt
		}
		if (replace && typeof replace === "object") {
			translated_text = format(translated_text, replace)
		}

		return translated_text
	}

	function format(str, args) {
		if (str == undefined) return str

		let unkeyed_index = 0
		return str.replace(/\{(\w*)\}/g, (match, key) => {
			if (key === "") {
				key = unkeyed_index
				unkeyed_index++
			}
			if (key == +key) {
				return args[key] !== undefined ? args[key] : match
			}
		})
	}
}

export function shouldUseBootMessages(targetLang, serverLang, bootMessages) {
	return Boolean(targetLang && serverLang && targetLang === serverLang && bootMessages)
}

export function unwrapTranslationsPayload(payload) {
	return payload?.message && typeof payload.message === "object" ? payload.message : {}
}

export async function fetchTranslations({
	lang,
	origin = globalThis.location?.origin,
	fetchImpl = globalThis.fetch,
} = {}) {
	const url = new URL("/api/method/hrms.api.get_pwa_translations", origin)
	url.searchParams.set("lang", lang)

	const response = await fetchImpl(url, {
		cache: "no-store",
		headers: {
			Accept: "application/json",
		},
	})

	if (!response.ok) {
		throw new Error(`Failed to load translations for ${lang}`)
	}

	return unwrapTranslationsPayload(await response.json())
}

const { translate, load } = makeTranslationFunction()

export const translationsPlugin = {
	async isReady() {
		await load()
	},
	install(app) {
		const __ = translate
		app.config.globalProperties.__ = __
		app.provide("$translate", __)
	},
}
