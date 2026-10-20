import test from "node:test"
import assert from "node:assert/strict"

test("day detail loading keeps the latest selected date when requests finish out of order", async () => {
	const { useAttendanceDayDetails } = await import("./attendanceDayDetails.js")
	const pending = new Map()
	const detail = useAttendanceDayDetails(
		({ date }) => new Promise((resolve) => pending.set(date, resolve))
	)
	const first = detail.load("2026-09-11", "employee")
	const second = detail.load("2026-09-12", "employee")
	pending.get("2026-09-12")({ attendance_date: "2026-09-12", working_hours: 7.5 })
	await second
	pending.get("2026-09-11")({ attendance_date: "2026-09-11", working_hours: 5.5 })
	await first
	assert.equal(detail.state.data.attendance_date, "2026-09-12")
	assert.equal(detail.state.data.working_hours, 7.5)
	assert.equal(detail.state.loading, false)
})

test("closing a day ignores a response that arrives afterward", async () => {
	const { useAttendanceDayDetails } = await import("./attendanceDayDetails.js")
	let finish
	const detail = useAttendanceDayDetails(
		() =>
			new Promise((resolve) => {
				finish = resolve
			})
	)
	const request = detail.load("2026-09-11", "employee")
	detail.reset()
	finish({ attendance_date: "2026-09-11", working_hours: 5.5 })
	await request
	assert.equal(detail.state.data, null)
	assert.equal(detail.state.date, null)
	assert.equal(detail.state.loading, false)
})

test("a failed request is visible and can be retried without retaining old records", async () => {
	const { useAttendanceDayDetails } = await import("./attendanceDayDetails.js")
	let fail = true
	const detail = useAttendanceDayDetails(async ({ date }) => {
		if (fail) throw new Error("Network unavailable")
		return { attendance_date: date, working_hours: 0 }
	})
	await detail.load("2026-09-11", "employee")
	assert.equal(detail.state.data, null)
	assert.equal(detail.state.error.message, "Network unavailable")
	assert.equal(detail.state.loading, false)
	fail = false
	await detail.load("2026-09-11", "employee")
	assert.equal(detail.state.error, null)
	assert.equal(detail.state.data.working_hours, 0)
})

test("hour formatting distinguishes zero from a pending total", async () => {
	const { formatDetailHours } = await import("./attendanceDayDetails.js")
	assert.equal(formatDetailHours(0), "0")
	assert.equal(formatDetailHours(5.5), "5.5")
	assert.equal(formatDetailHours(9.18), "9.18")
	assert.equal(formatDetailHours(null), "—")
})

test("overnight clock times keep their date instead of looking earlier than check-in", async () => {
	const { formatDetailTime } = await import("./attendanceDayDetails.js")
	assert.equal(formatDetailTime("2026-09-11 08:55:51", "2026-09-11", true), "08:55:51")
	assert.equal(formatDetailTime("2026-09-12 00:30:09", "2026-09-11", true), "9/12 00:30:09")
	assert.equal(formatDetailTime("2026-09-12T06:30:00", "2026-09-11"), "9/12 06:30")
})
