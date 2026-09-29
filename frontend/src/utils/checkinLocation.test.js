import test from "node:test"
import assert from "node:assert/strict"

import {
	acquireCheckinLocation,
	locationFailureAdvice,
	reportLocationFailure,
	shouldRequestLocation,
	submitQrCheckin,
} from "./checkinLocation.js"

// 按顺序回应每次定位请求：{ accuracy, latitude?, longitude?, after? } 是拿到位置，{ code } 是失败
function fakeGeolocation(steps, clock = { now: 0 }) {
	const requests = []
	return {
		requests,
		getCurrentPosition(onSuccess, onError, options) {
			requests.push(options)
			const step = steps[requests.length - 1]
			if (!step) throw new Error("unexpected extra location request")
			clock.now += step.after || 0
			if (step.throws) throw new Error("blocked")
			if (step.code) {
				onError({ code: step.code, message: "native message" })
				return
			}
			onSuccess({
				coords: {
					latitude: step.latitude ?? 35.6813,
					longitude: step.longitude ?? 139.7672,
					accuracy: step.accuracy,
				},
				timestamp: 0,
			})
		},
	}
}

test("uses a quick fix right away when it is accurate enough", async () => {
	const geolocation = fakeGeolocation([{ accuracy: 35 }])
	const result = await acquireCheckinLocation({ geolocation })
	assert.equal(result.ok, true)
	assert.equal(result.accuracy, 35)
	assert.equal(geolocation.requests.length, 1)
	assert.equal(geolocation.requests[0].enableHighAccuracy, false)
	assert.ok(geolocation.requests[0].maximumAge > 0, "a position from a few seconds ago is fine")
	assert.ok(geolocation.requests[0].timeout <= 8000)
})

test("asks once for a precise fix when the quick one is too rough", async () => {
	const geolocation = fakeGeolocation([{ accuracy: 900 }, { accuracy: 40, latitude: 35.7 }])
	const result = await acquireCheckinLocation({ geolocation })
	assert.equal(geolocation.requests.length, 2)
	assert.equal(geolocation.requests[1].enableHighAccuracy, true)
	assert.deepEqual([result.ok, result.accuracy, result.latitude], [true, 40, 35.7])
})

test("keeps the rough fix when the precise attempt fails or is worse", async () => {
	for (const second of [{ code: 3 }, { accuracy: 1500 }]) {
		const geolocation = fakeGeolocation([{ accuracy: 900 }, second])
		const result = await acquireCheckinLocation({ geolocation })
		assert.deepEqual([result.ok, result.accuracy], [true, 900])
	}
})

test("a refused permission is reported at once without asking again", async () => {
	const geolocation = fakeGeolocation([{ code: 1 }])
	const result = await acquireCheckinLocation({ geolocation })
	assert.deepEqual([result.ok, result.reason], [false, "denied"])
	assert.equal(geolocation.requests.length, 1)
})

test("tells a timeout apart from an unavailable position", async () => {
	const timeout = await acquireCheckinLocation({ geolocation: fakeGeolocation([{ code: 3 }]) })
	const unavailable = await acquireCheckinLocation({ geolocation: fakeGeolocation([{ code: 2 }]) })
	assert.equal(timeout.reason, "timeout")
	assert.equal(unavailable.reason, "unavailable")
})

test("a browser without location support, or one that blocks the request, is handled", async () => {
	const unsupported = await acquireCheckinLocation({ geolocation: undefined })
	const blocked = await acquireCheckinLocation({ geolocation: fakeGeolocation([{ throws: true }]) })
	assert.equal(unsupported.reason, "unsupported")
	assert.equal(blocked.reason, "unavailable")
})

test("reports how long the phone took", async () => {
	const clock = { now: 1000 }
	const geolocation = fakeGeolocation([{ accuracy: 900, after: 2000 }, { code: 3, after: 1200 }], clock)
	const result = await acquireCheckinLocation({ geolocation, now: () => clock.now })
	assert.equal(result.elapsedMs, 3200)
})

test("each failure gets its own advice in every language", () => {
	for (const lang of ["ja", "zh", "en"]) {
		const advice = ["denied", "timeout", "unsupported"].map((reason) => locationFailureAdvice(reason, lang))
		assert.equal(new Set(advice).size, 3, lang)
		assert.ok(advice.every((text) => text.length > 0), lang)
		assert.equal(locationFailureAdvice("unavailable", lang), locationFailureAdvice("timeout", lang))
	}
	assert.equal(locationFailureAdvice("denied", "fr"), locationFailureAdvice("denied", "zh"))
	assert.equal(locationFailureAdvice("something-new", "ja"), locationFailureAdvice("timeout", "ja"))
})

test("only skips the location when the server says it is not needed", () => {
	assert.equal(shouldRequestLocation({ location_required: false }), false)
	assert.equal(shouldRequestLocation({ location_required: true }), true)
	assert.equal(shouldRequestLocation(null), true)
})

test("reports a failure with flow, reason and wait time, and never throws", async () => {
	const calls = []
	await reportLocationFailure(async (method, params) => calls.push([method, params]), {
		flow: "qr",
		reason: "denied",
		elapsedMs: 1234,
	})
	assert.deepEqual(calls, [
		["hrms.api.checkin_location.report_location_failure", { flow: "qr", reason: "denied", elapsed_ms: 1234 }],
	])
	await reportLocationFailure(
		async () => {
			throw new Error("offline")
		},
		{ flow: "qr", reason: "timeout", elapsedMs: 1 }
	)
})

function fakeServer(responses) {
	const calls = []
	return {
		calls,
		call: async (method, params) => {
			calls.push([method, params])
			const response = responses[calls.length - 1]
			if (response instanceof Error) throw response
			return response
		},
	}
}

test("submits a QR check-in once with the position it already has", async () => {
	const server = fakeServer([{ status: "ok", message: "done" }])
	const result = await submitQrCheckin({
		call: server.call,
		token: "door|1|sig",
		logType: "IN",
		position: { latitude: 35.6, longitude: 139.7 },
		locate: async () => assert.fail("should not locate again"),
	})
	assert.equal(result.outcome, "success")
	assert.deepEqual(server.calls, [
		["hrms.api.qr_attendance.qr_checkin", { token: "door|1|sig", log_type: "IN", latitude: 35.6, longitude: 139.7 }],
	])
})

test("locates and resubmits when the server asks for a location", async () => {
	const server = fakeServer([{ status: "need_location" }, { status: "ok" }])
	const result = await submitQrCheckin({
		call: server.call,
		token: "door|1|sig",
		logType: "OUT",
		locate: async () => ({ ok: true, latitude: 35.6, longitude: 139.7, accuracy: 30 }),
	})
	assert.equal(result.outcome, "success")
	assert.deepEqual(server.calls[0][1], { token: "door|1|sig", log_type: "OUT" })
	assert.deepEqual(server.calls[1][1], { token: "door|1|sig", log_type: "OUT", latitude: 35.6, longitude: 139.7 })
})

test("stops with the reason when the location still can't be found", async () => {
	const server = fakeServer([{ status: "need_location" }])
	const failed = { ok: false, reason: "denied", elapsedMs: 5 }
	const result = await submitQrCheckin({ call: server.call, token: "t", logType: "IN", locate: async () => failed })
	assert.deepEqual(result, { outcome: "location_failed", reason: "denied", location: failed })
	assert.equal(server.calls.length, 1)
})

test("passes server errors through", async () => {
	const server = fakeServer([new Error("QR code has expired")])
	const result = await submitQrCheckin({ call: server.call, token: "t", logType: "IN", locate: async () => null })
	assert.deepEqual(result, { outcome: "error", message: "QR code has expired" })
})
