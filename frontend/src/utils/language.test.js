import test from "node:test"
import assert from "node:assert/strict"

import {
	PWA_LANGUAGE_STORAGE_KEY,
	PWA_LANGUAGE_OPTIONS,
	normalizeLanguage,
	getStoredLanguage,
	resolveEffectiveLanguage,
	initializeBootLanguage,
	changeLanguage,
} from "./language.js"

function createStorage(initialState = {}) {
	const state = new Map(Object.entries(initialState))
	return {
		getItem(key) {
			return state.has(key) ? state.get(key) : null
		},
		setItem(key, value) {
			state.set(key, value)
		},
		removeItem(key) {
			state.delete(key)
		},
	}
}

test("normalizes browser and Frappe language variants", () => {
	assert.equal(normalizeLanguage("zh-CN"), "zh")
	assert.equal(normalizeLanguage("ja_JP"), "ja")
	assert.equal(normalizeLanguage("en-US"), "en")
	assert.equal(normalizeLanguage("fr"), null)
})

test("returns only supported stored languages", () => {
	const supportedStorage = createStorage({ [PWA_LANGUAGE_STORAGE_KEY]: "ja" })
	const unsupportedStorage = createStorage({ [PWA_LANGUAGE_STORAGE_KEY]: "fr" })

	assert.equal(getStoredLanguage(supportedStorage), "ja")
	assert.equal(getStoredLanguage(unsupportedStorage), null)
})

test("prefers stored language over the server boot language", () => {
	const storage = createStorage({ [PWA_LANGUAGE_STORAGE_KEY]: "en" })
	const boot = { lang: "zh-CN" }

	assert.equal(resolveEffectiveLanguage({ boot, storage }), "en")
})

test("initializes server_lang and effective lang on boot", () => {
	const storage = createStorage({ [PWA_LANGUAGE_STORAGE_KEY]: "ja" })
	const boot = { lang: "zh-CN" }

	assert.deepEqual(initializeBootLanguage({ boot, storage }), {
		serverLang: "zh",
		effectiveLang: "ja",
	})
	assert.equal(boot.server_lang, "zh")
	assert.equal(boot.lang, "ja")
})

test("persists the requested language and triggers reload", () => {
	const storage = createStorage()
	let reloaded = false
	const boot = { lang: "zh", server_lang: "zh" }

	const selected = changeLanguage("en", {
		boot,
		storage,
		reload: () => {
			reloaded = true
		},
	})

	assert.equal(selected, "en")
	assert.equal(storage.getItem(PWA_LANGUAGE_STORAGE_KEY), "en")
	assert.equal(boot.lang, "en")
	assert.equal(reloaded, true)
})

test("exports the exact three language options used by the UI", () => {
	assert.deepEqual(PWA_LANGUAGE_OPTIONS, [
		{ value: "zh", shortLabel: "中", label: "中文" },
		{ value: "ja", shortLabel: "日", label: "日本語" },
		{ value: "en", shortLabel: "EN", label: "English" },
	])
})
