import test from "node:test"
import assert from "node:assert/strict"

import {
	computeProgress,
	deriveAttendanceState,
	formatWorkHours,
	isOvertime,
	OVERTIME_HOURS,
	summarizeMonth,
} from "./attendanceCalendarState.js"

// hasAttendanceAnomaly keys off anomaly.has_issue, so a payload carrying only a
// code is not an anomaly.
test("an anomaly outranks every other signal", () => {
	const entry = { anomaly: { has_issue: true, codes: ["missing_checkout"] }, attendance: "Present" }
	assert.equal(deriveAttendanceState(entry, { weekly_off: 0 }), "anomaly")
	assert.equal(
		deriveAttendanceState({ anomaly: { has_issue: false }, attendance: "Present" }, null),
		"work"
	)
})

test("attendance status maps to a cell state", () => {
	assert.equal(deriveAttendanceState({ attendance: "Present" }, null), "work")
	assert.equal(deriveAttendanceState({ attendance: "Work From Home" }, null), "wfh")
	assert.equal(deriveAttendanceState({ attendance: "Half Day" }, null), "half")
	assert.equal(deriveAttendanceState({ attendance: "On Leave" }, null), "leave")
	assert.equal(deriveAttendanceState({ attendance: "Holiday" }, null), "holiday")
})

// Absent is deliberately shown as rest until the business separates the two.
test("absent still renders as rest", () => {
	assert.equal(deriveAttendanceState({ attendance: "Absent" }, null), "rest")
})

test("holidays and weekly offs are distinguished", () => {
	assert.equal(deriveAttendanceState({}, { weekly_off: 0, description: "山の日" }), "holiday")
	assert.equal(deriveAttendanceState({}, { weekly_off: 1 }), "rest")
})

// The whole point of the redesign: a rostered future day is no longer a special
// state, it is simply a day with nothing recorded yet.
test("a day with no attendance record is empty regardless of roster", () => {
	assert.equal(deriveAttendanceState({}, null), "empty")
	assert.equal(deriveAttendanceState(null, null), "empty")
})

test("overtime starts at ten hours", () => {
	assert.equal(OVERTIME_HOURS, 10)
	assert.equal(isOvertime(9.9), false)
	assert.equal(isOvertime(10), true)
	assert.equal(isOvertime(10.1), true)
	assert.equal(isOvertime(0), false)
	assert.equal(isOvertime(null), false)
})

test("work hours drop a trailing zero", () => {
	assert.equal(formatWorkHours(8), "8")
	assert.equal(formatWorkHours(8.0), "8")
	assert.equal(formatWorkHours(8.5), "8.5")
	assert.equal(formatWorkHours(8.46), "8.5")
	assert.equal(formatWorkHours(0), "")
	assert.equal(formatWorkHours(null), "")
	assert.equal(formatWorkHours(undefined), "")
})

test("summarizeMonth counts wfh as a full day and half as a half", () => {
	const cells = [
		{ state: "work", hours: 8 },
		{ state: "wfh", hours: 7 },
		{ state: "half", hours: 4 },
		{ state: "rest", hours: 0 },
		{ state: "empty", hours: 0 },
	]
	assert.deepEqual(summarizeMonth(cells), { workDays: 2.5, hours: 19, avg: 7.6 })
})

test("summarizeMonth does not divide by zero", () => {
	assert.deepEqual(summarizeMonth([{ state: "rest", hours: 0 }]), {
		workDays: 0,
		hours: 0,
		avg: 0,
	})
	assert.deepEqual(summarizeMonth([]), { workDays: 0, hours: 0, avg: 0 })
})

// With no roster data there is no denominator, and "23 / 0" would be nonsense.
test("computeProgress hides itself when nothing is scheduled", () => {
	const cells = [{ state: "work", hours: 8 }]
	assert.deepEqual(computeProgress(cells, 0), { visible: false, done: 1, total: 0, percent: 0 })
})

test("computeProgress reports done over total", () => {
	const cells = [
		{ state: "work", hours: 8 },
		{ state: "work", hours: 8 },
		{ state: "half", hours: 4 },
	]
	assert.deepEqual(computeProgress(cells, 10), { visible: true, done: 2.5, total: 10, percent: 25 })
})

test("computeProgress caps at one hundred percent", () => {
	const cells = Array.from({ length: 12 }, () => ({ state: "work", hours: 8 }))
	const progress = computeProgress(cells, 10)
	assert.equal(progress.percent, 100)
	assert.equal(progress.done, 12)
})
