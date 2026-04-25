import test from "node:test"
import assert from "node:assert/strict"

import {
	shouldUseBootMessages,
	unwrapTranslationsPayload,
	fetchTranslations,
} from "./translationsPlugin.js"

test("reuses boot messages only when the effective language matches server_lang", () => {
	assert.equal(shouldUseBootMessages("ja", "ja", { Settings: "設定" }), true)
	assert.equal(shouldUseBootMessages("en", "ja", { Settings: "設定" }), false)
	assert.equal(shouldUseBootMessages("ja", "ja", null), false)
})

test("unwraps Frappe method payloads into a plain message dictionary", () => {
	assert.deepEqual(unwrapTranslationsPayload({ message: { Settings: "設定" } }), {
		Settings: "設定",
	})
	assert.deepEqual(unwrapTranslationsPayload({}), {})
})

test("fetchTranslations calls the HRMS translation endpoint for the requested language", async () => {
	let requestedUrl = ""

	const messages = await fetchTranslations({
		lang: "en",
		origin: "https://example.com",
		fetchImpl: async (url) => {
			requestedUrl = url.toString()
			return {
				ok: true,
				async json() {
					return { message: { Settings: "Settings" } }
				},
			}
		},
	})

	assert.equal(
		requestedUrl,
		"https://example.com/api/method/hrms.api.get_pwa_translations?lang=en",
	)
	assert.deepEqual(messages, { Settings: "Settings" })
})
