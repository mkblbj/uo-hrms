import test from "node:test"
import assert from "node:assert/strict"

import { easeOutCubic, interpolateCountUp, formatCountUp } from "./homeCountUp.js"

test("easeOutCubic clamps to [0, 1] and matches reference values", () => {
	assert.equal(easeOutCubic(0), 0)
	assert.equal(easeOutCubic(1), 1)
	assert.equal(easeOutCubic(0.5), 1 - Math.pow(0.5, 3))
	assert.equal(easeOutCubic(-0.5), 0)
	assert.equal(easeOutCubic(1.5), 1)
})

test("interpolateCountUp follows ease-out curve, never overshoots", () => {
	const start = 0
	const target = 122.5
	const mid = interpolateCountUp(start, target, 0.5)
	const end = interpolateCountUp(start, target, 1)
	const before = interpolateCountUp(start, target, 0)

	assert.equal(before, start)
	assert.equal(end, target)
	assert.ok(mid > target * 0.5, "ease-out should be past 50% of target at progress 0.5")
	assert.ok(mid < target, "should not overshoot")
})

test("interpolateCountUp handles negative deltas and decimals", () => {
	assert.equal(interpolateCountUp(10, 5, 0), 10)
	assert.equal(interpolateCountUp(10, 5, 1), 5)
})

test("formatCountUp returns integer string when decimals = 0", () => {
	assert.equal(formatCountUp(122.7, 0), "123")
	assert.equal(formatCountUp(0, 0), "0")
})

test("formatCountUp returns fixed decimals when decimals > 0", () => {
	assert.equal(formatCountUp(122.7, 1), "122.7")
	assert.equal(formatCountUp(0, 1), "0.0")
	assert.equal(formatCountUp(8, 2), "8.00")
})

test("formatCountUp handles NaN / non-finite gracefully", () => {
	assert.equal(formatCountUp(NaN, 1), "0.0")
	assert.equal(formatCountUp(Infinity, 0), "0")
})
