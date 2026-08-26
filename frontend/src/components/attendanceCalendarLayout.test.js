import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import {
	padCalendarDaysToFullWeeks,
	getCalendarWeekCount,
	getCalendarGridStyle,
} from "./attendanceCalendarLayout.js"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const attendanceCalendarPath = path.resolve(currentDir, "AttendanceCalendar.vue")

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
		gridTemplateRows: "repeat(5, minmax(56px, 1fr))",
	})
	assert.deepEqual(getCalendarGridStyle(6), {
		gridTemplateRows: "repeat(6, minmax(56px, 1fr))",
	})
})

// The monthly numbers used to live in a strip pinned under the grid. They are
// the page's conclusion, so they now render above it through a dedicated
// component; the doesNotMatch lines below still guard the older layouts this
// page has already moved away from.
test("delegates the monthly numbers to the summary component", () => {
	const source = fs.readFileSync(attendanceCalendarPath, "utf8")

	assert.match(source, /<AttendanceMonthSummary/)
	assert.doesNotMatch(source, /month-summary-strip/)
	assert.doesNotMatch(source, /class="month-meta"/)
	assert.doesNotMatch(source, /class="detail-strip"\s+v-if="selectedCell"/)
	assert.doesNotMatch(source, /<component\s+:is="DetailMain"\s+:cell="selectedCell"/)
})

test("renders attendance anomaly state in the monthly calendar", () => {
	const source = fs.readFileSync(attendanceCalendarPath, "utf8")

	assert.match(source, /getAttendanceAnomalyLabel/)
	assert.match(source, /state === "anomaly"/)
	assert.match(source, /dlg-anomaly-reason/)
})
