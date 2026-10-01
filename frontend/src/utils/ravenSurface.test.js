import test from "node:test"
import assert from "node:assert/strict"

import { RAVEN_SURFACE, RAVEN_THEME_KEY, ravenSurfaceColor } from "./ravenSurface.js"

// Raven keeps its own light/dark choice, separate from the app's 8:00–16:00 rule:
// localStorage "raven-theme" holds light, dark or system, and system — also the
// default when nothing is stored — follows the phone.
test("an explicit Raven choice wins over the phone setting", () => {
	assert.equal(ravenSurfaceColor({ stored: "light", systemDark: true }), RAVEN_SURFACE.light)
	assert.equal(ravenSurfaceColor({ stored: "dark", systemDark: false }), RAVEN_SURFACE.dark)
})

test("system, nothing stored, or anything unknown follows the phone", () => {
	for (const stored of ["system", null, undefined, "", "sepia"]) {
		assert.equal(ravenSurfaceColor({ stored, systemDark: true }), RAVEN_SURFACE.dark, String(stored))
		assert.equal(ravenSurfaceColor({ stored, systemDark: false }), RAVEN_SURFACE.light, String(stored))
	}
})

// The values of Raven's --surface-base, the background of its top bar.
test("the surface colours match Raven's top bar", () => {
	assert.deepEqual(RAVEN_SURFACE, { light: "#ffffff", dark: "#171717" })
	assert.equal(RAVEN_THEME_KEY, "raven-theme")
})
