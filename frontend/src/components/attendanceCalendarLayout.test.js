import test from "node:test"
import assert from "node:assert/strict"

import {
	padCalendarDaysToFullWeeks,
	getCalendarWeekCount,
	getCalendarGridStyle,
} from "./attendanceCalendarLayout.js"

test("pads trailing empty cells to complete a five-week calendar", () => {
	const days = Array.from({ length: 33 }, (_, index) => ({ date: index + 1 }))

	const paddedDays = padCalendarDaysToFullWeeks(days)

	assert.equal(paddedDays.length, 35)
	assert.deepEqual(paddedDays.slice(-2), [{ empty: true }, { empty: true }])
})

test("pads trailing empty cells to complete a six-week calendar", () => {
	const days = Array.from({ length: 36 }, (_, index) => ({ date: index + 1 }))

	const paddedDays = padCalendarDaysToFullWeeks(days)

	assert.equal(paddedDays.length, 42)
	assert.deepEqual(paddedDays.slice(-6), Array.from({ length: 6 }, () => ({ empty: true })))
})

test("returns the rendered week count for padded calendar days", () => {
	assert.equal(getCalendarWeekCount([]), 0)
	assert.equal(getCalendarWeekCount(Array.from({ length: 35 }, () => ({ empty: true }))), 5)
	assert.equal(getCalendarWeekCount(Array.from({ length: 42 }, () => ({ empty: true }))), 6)
})

test("builds grid row styles that evenly divide the calendar by week count", () => {
	assert.deepEqual(getCalendarGridStyle(0), {})
	assert.deepEqual(getCalendarGridStyle(5), {
		gridTemplateRows: "repeat(5, minmax(0, 1fr))",
	})
	assert.deepEqual(getCalendarGridStyle(6), {
		gridTemplateRows: "repeat(6, minmax(0, 1fr))",
	})
})
