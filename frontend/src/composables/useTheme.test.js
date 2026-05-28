import assert from "node:assert/strict"
import { test } from "node:test"

import { resolveTheme, THEME_STORAGE_KEY } from "./useTheme.js"

test("resolveTheme returns 'dark' when OS prefers dark and no override", () => {
	assert.equal(resolveTheme({ osPrefersDark: true, stored: null }), "dark")
})

test("resolveTheme returns 'light' when OS prefers light and no override", () => {
	assert.equal(resolveTheme({ osPrefersDark: false, stored: null }), "light")
})

test("resolveTheme returns stored override regardless of OS preference", () => {
	assert.equal(resolveTheme({ osPrefersDark: true, stored: "light" }), "light")
	assert.equal(resolveTheme({ osPrefersDark: false, stored: "dark" }), "dark")
})

test("resolveTheme ignores invalid stored values", () => {
	assert.equal(resolveTheme({ osPrefersDark: true, stored: "banana" }), "dark")
	assert.equal(resolveTheme({ osPrefersDark: false, stored: "" }), "light")
})

test("THEME_STORAGE_KEY is a stable string", () => {
	assert.equal(typeof THEME_STORAGE_KEY, "string")
	assert.ok(THEME_STORAGE_KEY.length > 0)
})
