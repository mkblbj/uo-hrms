import test from "node:test"
import assert from "node:assert/strict"

import {
	DEFAULT_STANDARD_DAY_HOURS,
	buildHeatmapMonthMarkers,
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

test("maps non-attendance days to a single quiet gray color", () => {
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
		"#e2e8f0"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: { attendance: "On Leave" },
			date: "2026-05-12",
			today: "2026-05-14",
		}).color,
		"#e2e8f0"
	)
	assert.equal(
		getAttendanceHeatmapCellMeta({
			event: null,
			date: "2026-05-13",
			today: "2026-05-14",
		}).color,
		"#e2e8f0"
	)
})

test("maps attendance anomalies to red before normal heat levels", () => {
	const meta = getAttendanceHeatmapCellMeta({
		event: {
			attendance: "Present",
			working_hours: 8,
			anomaly: { has_issue: true, codes: ["missing_checkout"] },
		},
		date: "2026-05-11",
		today: "2026-05-14",
	})

	assert.equal(meta.color, "#dc2626")
	assert.equal(meta.hasIssue, true)
	assert.equal(meta.level, 0)
})

test("builds a 13 week by 7 day grid ending at the current week", () => {
	const cells = buildRecentWeekdayHeatmap({
		events: {
			"2026-05-11": { attendance: "Present", working_hours: 8 },
			"2026-05-12": { attendance: "Half Day" },
			"2026-05-17": { attendance: "Present", working_hours: 3 },
		},
		today: "2026-05-14",
	})

	assert.equal(cells.length, 91)
	assert.equal(cells[0].weekday, 1)
	assert.equal(cells.at(-1).weekday, 7)
	assert.ok(cells.some((cell) => cell.date === "2026-05-11" && cell.level === 4))
	assert.ok(cells.some((cell) => cell.date === "2026-05-12" && cell.level === 2))
	assert.ok(cells.some((cell) => cell.date === "2026-05-17" && cell.weekday === 7))
	assert.ok(cells.some((cell) => cell.date === "2026-05-14" && cell.isToday))
	assert.ok(cells.some((cell) => cell.date === "2026-05-15" && cell.isFuture))
})

test("builds month markers for the first week and month transitions", () => {
	const cells = buildRecentWeekdayHeatmap({ today: "2026-05-14" })
	const markers = buildHeatmapMonthMarkers({ cells, lang: "zh" })

	assert.equal(markers.length, 13)
	assert.equal(markers[0].label, "2月")
	assert.ok(markers.some((marker) => marker.label === "3月"))
	assert.ok(markers.some((marker) => marker.label === "4月"))
	assert.ok(markers.some((marker) => marker.label === "5月"))
	assert.ok(markers.some((marker) => marker.label === ""))
})
