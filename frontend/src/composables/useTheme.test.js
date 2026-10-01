import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { test } from "node:test"
import { fileURLToPath } from "node:url"

import {
	applyThemeToDocument,
	getBoundaryDelay,
	getNextBoundary,
	LEGACY_THEME_KEY,
	readOverride,
	resolveTheme,
	THEME_OVERRIDE_KEY,
	THEME_PAGE_COLORS,
	writeOverride,
} from "./useTheme.js"

const at = (year, month, day, hour, minute = 0) => new Date(year, month - 1, day, hour, minute)

function withStorage(initial, run) {
	const store = new Map(Object.entries(initial))
	globalThis.localStorage = {
		getItem: (key) => (store.has(key) ? store.get(key) : null),
		setItem: (key, value) => store.set(key, String(value)),
		removeItem: (key) => store.delete(key),
	}
	try {
		return run(store)
	} finally {
		delete globalThis.localStorage
	}
}

test("daylight hours resolve to light", () => {
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 8), override: null }), "light")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 12), override: null }), "light")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 15, 59), override: null }), "light")
})

test("evening and small hours resolve to dark", () => {
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 16), override: null }), "dark")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 23, 59), override: null }), "dark")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 0), override: null }), "dark")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 7, 59), override: null }), "dark")
})

test("an override holds for the rest of its window", () => {
	const override = { theme: "dark", at: at(2026, 8, 11, 14).getTime() }
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 14, 1), override }), "dark")
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 15, 59), override }), "dark")
})

test("an override expires at the next boundary", () => {
	const afternoon = { theme: "dark", at: at(2026, 8, 11, 14).getTime() }
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 17), override: afternoon }), "dark")
	assert.equal(resolveTheme({ now: at(2026, 8, 12, 9), override: afternoon }), "light")

	const evening = { theme: "light", at: at(2026, 8, 11, 20).getTime() }
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 22), override: evening }), "light")
	assert.equal(resolveTheme({ now: at(2026, 8, 12, 22), override: evening }), "dark")
})

// The dark window straddles midnight, so an override set at 23:00 must still
// apply at 02:00 — they are the same window, not two.
test("an override set before midnight still applies after it", () => {
	const override = { theme: "light", at: at(2026, 8, 11, 23).getTime() }
	assert.equal(resolveTheme({ now: at(2026, 8, 12, 2), override }), "light")
	assert.equal(resolveTheme({ now: at(2026, 8, 12, 9), override }), "light")
	assert.equal(resolveTheme({ now: at(2026, 8, 12, 17), override }), "dark")
})

test("malformed overrides fall back to the time window", () => {
	const now = at(2026, 8, 11, 12)
	assert.equal(resolveTheme({ now, override: { theme: "banana", at: now.getTime() } }), "light")
	assert.equal(resolveTheme({ now, override: { theme: "dark", at: "soon" } }), "light")
	assert.equal(resolveTheme({ now, override: { theme: "dark", at: Number.NaN } }), "light")
	assert.equal(resolveTheme({ now, override: { theme: "dark" } }), "light")
	assert.equal(resolveTheme({ now, override: "dark" }), "light")
	assert.equal(resolveTheme({ now, override: null }), "light")
})

// A user who moves the device clock backwards would otherwise be stuck with an
// override dated in the future, which no boundary can ever expire.
test("an override from the future is ignored", () => {
	const override = { theme: "dark", at: at(2026, 8, 12, 12).getTime() }
	assert.equal(resolveTheme({ now: at(2026, 8, 11, 12), override }), "light")
})

test("getNextBoundary returns the end of the current window", () => {
	assert.deepEqual(getNextBoundary(at(2026, 8, 11, 9)), at(2026, 8, 11, 16))
	assert.deepEqual(getNextBoundary(at(2026, 8, 11, 18)), at(2026, 8, 12, 8))
	assert.deepEqual(getNextBoundary(at(2026, 8, 11, 3)), at(2026, 8, 11, 8))
})

test("getNextBoundary is strictly in the future on a boundary itself", () => {
	assert.deepEqual(getNextBoundary(at(2026, 8, 11, 8)), at(2026, 8, 11, 16))
	assert.deepEqual(getNextBoundary(at(2026, 8, 11, 16)), at(2026, 8, 12, 8))
})

test("readOverride parses a stored override", () => {
	const stored = JSON.stringify({ theme: "dark", at: 1786000000000 })
	withStorage({ [THEME_OVERRIDE_KEY]: stored }, () => {
		assert.deepEqual(readOverride(), { theme: "dark", at: 1786000000000 })
	})
})

test("readOverride returns null for unparseable storage", () => {
	withStorage({ [THEME_OVERRIDE_KEY]: "{not json" }, () => {
		assert.equal(readOverride(), null)
	})
})

// The old key stored a bare "light"/"dark" meaning "override forever". That
// meaning is gone, so reading it must clear it rather than carry it over.
test("readOverride drops the legacy preference key", () => {
	withStorage({ [LEGACY_THEME_KEY]: "dark" }, (store) => {
		assert.equal(readOverride(), null)
		assert.equal(store.has(LEGACY_THEME_KEY), false)
	})
})

test("writeOverride stores theme and timestamp together", () => {
	withStorage({}, (store) => {
		writeOverride("light", 1786000000000)
		assert.deepEqual(JSON.parse(store.get(THEME_OVERRIDE_KEY)), {
			theme: "light",
			at: 1786000000000,
		})
	})
})

test("storage failures leave the caller with no override", () => {
	globalThis.localStorage = {
		getItem() {
			throw new Error("blocked")
		},
		setItem() {
			throw new Error("blocked")
		},
		removeItem() {
			throw new Error("blocked")
		},
	}
	try {
		assert.equal(readOverride(), null)
		assert.doesNotThrow(() => writeOverride("dark", 1786000000000))
	} finally {
		delete globalThis.localStorage
	}
})

test("storage keys are stable strings", () => {
	assert.equal(THEME_OVERRIDE_KEY, "hrms_theme_override")
	assert.equal(LEGACY_THEME_KEY, "hrms_theme_preference")
})

test("getBoundaryDelay counts the milliseconds to the next boundary", () => {
	assert.equal(getBoundaryDelay(at(2026, 8, 11, 15)), 60 * 60 * 1000)
	assert.equal(getBoundaryDelay(at(2026, 8, 11, 7)), 60 * 60 * 1000)
	assert.equal(getBoundaryDelay(at(2026, 8, 11, 16)), 16 * 60 * 60 * 1000)
})

// setTimeout with a zero or negative delay would fire immediately and re-arm in
// a tight loop, so the delay is floored to a second.
test("getBoundaryDelay never returns less than a second", () => {
	assert.ok(getBoundaryDelay(at(2026, 8, 11, 15, 59)) >= 1000)
	assert.equal(getBoundaryDelay(new Date(at(2026, 8, 11, 16).getTime() - 1)), 1000)
})

function fakeDocument({ withMeta = true } = {}) {
	const attributes = {}
	const meta = withMeta ? { content: "#fff", setAttribute: (name, value) => { meta[name] = value } } : null
	return {
		attributes,
		meta,
		documentElement: { setAttribute: (name, value) => { attributes[name] = value } },
		querySelector: (selector) => (selector === 'meta[name="theme-color"]' ? meta : null),
	}
}

// Older iOS and Android still tint the status bar from theme-color, so it has
// to follow the app's own theme — prefers-color-scheme is frozen per process in
// a standalone web app and would never see a time-based switch.
test("applying a theme updates data-theme and theme-color together", () => {
	const doc = fakeDocument()
	applyThemeToDocument(doc, "dark")
	assert.equal(doc.attributes["data-theme"], "dark")
	assert.equal(doc.meta.content, THEME_PAGE_COLORS.dark)

	applyThemeToDocument(doc, "light")
	assert.equal(doc.attributes["data-theme"], "light")
	assert.equal(doc.meta.content, THEME_PAGE_COLORS.light)
})

test("a page without a theme-color meta still gets its theme", () => {
	const doc = fakeDocument({ withMeta: false })
	assert.doesNotThrow(() => applyThemeToDocument(doc, "dark"))
	assert.equal(doc.attributes["data-theme"], "dark")
})

// The constants duplicate --h-bg-page so the meta can be set without a style
// recalculation; this keeps the two from drifting apart.
test("theme page colours match the --h-bg-page tokens", () => {
	const tokensPath = path.resolve(
		path.dirname(fileURLToPath(import.meta.url)),
		"../theme/home-tokens.css"
	)
	const tokens = fs.readFileSync(tokensPath, "utf8")
	const light = tokens.match(/:root\s*\{[\s\S]*?--h-bg-page:\s*([^;]+);/)[1].trim()
	const dark = tokens.match(/\[data-theme="dark"\]\s*\{[\s\S]*?--h-bg-page:\s*([^;]+);/)[1].trim()
	assert.deepEqual(THEME_PAGE_COLORS, { light, dark })
})
