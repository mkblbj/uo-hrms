import test from "node:test"
import assert from "node:assert/strict"

import { shouldPlayIntro, markIntroPlayed, INTRO_KEY } from "./homeIntroAnimation.js"

function makeStorage(initial = {}) {
	const store = { ...initial }
	return {
		getItem: (k) => (k in store ? store[k] : null),
		setItem: (k, v) => {
			store[k] = String(v)
		},
		_store: store,
	}
}

function makeMatchMedia(reducedMotion) {
	return (query) => ({
		matches: query.includes("reduce") ? reducedMotion : false,
	})
}

test("plays intro when storage empty and motion allowed", () => {
	const storage = makeStorage()
	const matchMedia = makeMatchMedia(false)
	assert.equal(shouldPlayIntro({ storage, matchMedia }), true)
})

test("skips intro when storage already flagged", () => {
	const storage = makeStorage({ [INTRO_KEY]: "1" })
	const matchMedia = makeMatchMedia(false)
	assert.equal(shouldPlayIntro({ storage, matchMedia }), false)
})

test("skips intro when user prefers reduced motion", () => {
	const storage = makeStorage()
	const matchMedia = makeMatchMedia(true)
	assert.equal(shouldPlayIntro({ storage, matchMedia }), false)
})

test("markIntroPlayed sets the flag", () => {
	const storage = makeStorage()
	markIntroPlayed({ storage })
	assert.equal(storage._store[INTRO_KEY], "1")
})

test("shouldPlayIntro returns false after markIntroPlayed", () => {
	const storage = makeStorage()
	const matchMedia = makeMatchMedia(false)
	assert.equal(shouldPlayIntro({ storage, matchMedia }), true)
	markIntroPlayed({ storage })
	assert.equal(shouldPlayIntro({ storage, matchMedia }), false)
})

test("handles missing storage / matchMedia gracefully (SSR-like)", () => {
	assert.equal(shouldPlayIntro({ storage: null, matchMedia: null }), false)
})

test("plays intro when matchMedia is null but storage is valid", () => {
	const storage = makeStorage()
	assert.equal(shouldPlayIntro({ storage, matchMedia: null }), true)
})
