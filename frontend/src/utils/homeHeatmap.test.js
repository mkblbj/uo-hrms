import test from "node:test"
import assert from "node:assert/strict"

import {
	DEFAULT_STANDARD_DAY_HOURS,
	buildRecentWeekdayHeatmap,
	getAttendanceHeatmapCellMeta,
} from "./homeHeatmap.js"

test("maps attendance statuses and working hours to fixed colors", () => {
	assert.equal(DEFAULT_STANDARD_DAY_HOURS, 8)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Present", working_hours: 2 },
			date: "2026-05-11",
			today: "2026-05-14",
		}).color,
		"#bbf7d0"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Present", working_hours: 6 },
			date: "2026-05-12",
			today: "2026-05-14",
		}).color,
		"#4ade80"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Present", working_hours: 10 },
			date: "2026-05-13",
			today: "2026-05-14",
		}).color,
		"#166534"
	)
})

test("maps holidays absences leave and future dates without fake work intensity", () => {
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Holiday" },
			date: "2026-05-10",
			today: "2026-05-14",
		}).color,
		"#e2e8f0"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Absent" },
			date: "2026-05-11",
			today: "2026-05-14",
		}).color,
		"#fecaca"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "On Leave" },
			date: "2026-05-12",
			today: "2026-05-14",
		}).color,
		"#fde68a"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "Present", working_hours: 8 },
			date: "2026-05-15",
			today: "2026-05-14",
		}).color,
		"#f1f5f9"
	)
})

test("builds a 13 week by 5 weekday grid ending at the current week", () => {
	const cells = buildRecentWeekdayHeatmap({
		events: {
			"2026-05-11": { attendance: "Present", working_hours: 8 },
			"2026-05-12": { attendance: "Half Day" },
		},
		today: "2026-05-14",
	})

	assert.equal(cells.length, 65)
	assert.equal(cells[0].weekday, 1)
	assert.equal(cells.at(-1).weekday, 5)
	assert.ok(cells.some((cell) => cell.date === "2026-05-11" && cell.level === 4))
	assert.ok(cells.some((cell) => cell.date === "2026-05-12" && cell.level === 2))
	assert.ok(cells.some((cell) => cell.date === "2026-05-15" && cell.isFuture))
})
