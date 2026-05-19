import test from "node:test"
import assert from "node:assert/strict"

import { buildShiftProgress } from "./homeShiftProgress.js"

const schedule = {
	date: "2026-05-19",
	start_time: "09:00",
	end_time: "18:00",
	scheduled_time: "09:00-18:00",
}

test("returns null when there is no usable schedule", () => {
	assert.equal(buildShiftProgress({ schedule: null }), null)
	assert.equal(buildShiftProgress({ schedule: { date: "2026-05-19" } }), null)
})

test("keeps progress at zero until the employee checks in", () => {
	const progress = buildShiftProgress({
		schedule,
		stats: {},
		workStatus: { status: "no_checkin_today" },
		now: "2026-05-19T10:30:00",
		lang: "zh",
	})

	assert.equal(progress.percent, 0)
	assert.equal(progress.statusLabel, "待出勤")
	assert.equal(progress.workedLabel, "0.0 / 9.0h")
	assert.equal(progress.rangeLabel, "09:00-18:00")
})

test("calculates live progress from the first check-in against scheduled duration", () => {
	const progress = buildShiftProgress({
		schedule,
		stats: { first_checkin_today: "2026-05-19 09:30:00" },
		workStatus: {
			status: "working",
			last_checkin: { log_type: "IN", time: "2026-05-19 09:30:00" },
		},
		now: "2026-05-19T13:30:00",
		lang: "zh",
	})

	assert.equal(progress.percent, 44.44)
	assert.equal(progress.statusLabel, "出勤中")
	assert.equal(progress.workedLabel, "4.0 / 9.0h")
})

test("uses the last check-out time for completed shifts", () => {
	const progress = buildShiftProgress({
		schedule,
		stats: {
			first_checkin_today: "2026-05-19 09:05:00",
			last_checkin_today: "2026-05-19 17:55:00",
		},
		workStatus: {
			status: "off_work",
			last_checkin: { log_type: "OUT", time: "2026-05-19 17:55:00" },
		},
		now: "2026-05-19T19:00:00",
		lang: "ja",
	})

	assert.equal(progress.percent, 98.15)
	assert.equal(progress.statusLabel, "退勤済")
	assert.equal(progress.workedLabel, "8.8 / 9.0h")
})

test("supports overnight shifts", () => {
	const progress = buildShiftProgress({
		schedule: {
			date: "2026-05-19",
			start_time: "22:00",
			end_time: "06:00",
			scheduled_time: "22:00-06:00",
		},
		stats: { first_checkin_today: "2026-05-19 22:10:00" },
		workStatus: {
			status: "working",
			last_checkin: { log_type: "IN", time: "2026-05-19 22:10:00" },
		},
		now: "2026-05-20T02:10:00",
		lang: "en",
	})

	assert.equal(progress.percent, 50)
	assert.equal(progress.statusLabel, "Working")
	assert.equal(progress.workedLabel, "4.0 / 8.0h")
})
