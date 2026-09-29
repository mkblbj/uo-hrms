import test from "node:test"
import assert from "node:assert/strict"

import {
	PASSKEY_MODE,
	QR_MODE,
	classifyWebAuthnError,
	createFrappeCaller,
	extractFrappeError,
	getSheetContent,
	needsLocation,
	resolveCheckinMode,
	runPasskeyCheckin,
	shouldShowWifiTip,
} from "./passkeyCheckin.js"
import { locationFailureAdvice } from "./checkinLocation.js"

function makeDeps(overrides = {}) {
	const calls = []
	const responses = {
		"hrms.api.passkey.register_options": { challenge: "reg" },
		"hrms.api.passkey.register_complete": { status: "ok" },
		"hrms.api.passkey.begin_checkin": { status: "ok", options: { challenge: "auth" }, evidence: "office_network" },
		"hrms.api.passkey.complete_checkin": { status: "ok", log_type: "IN", evidence: "office_network" },
		...overrides.responses,
	}
	return {
		calls,
		deps: {
			call: async (method, params) => {
				calls.push([method, params])
				const response = responses[method]
				if (typeof response === "function") return response(params, calls)
				if (response instanceof Error) throw response
				return response
			},
			startRegistration: overrides.startRegistration || (async () => ({ id: "cred" })),
			startAuthentication: overrides.startAuthentication || (async () => ({ id: "cred" })),
			getPosition: overrides.getPosition || (async () => ({ latitude: 35.6, longitude: 139.7, accuracy: 20 })),
			deviceName: () => "iPhone",
			now: () => 1000,
		},
	}
}

function namedError(name) {
	const error = new Error(name)
	error.name = name
	return error
}

const officeContext = { enabled: true, has_passkey: true, on_office_network: true }

test("mode needs both the server switch and platform support", () => {
	assert.equal(resolveCheckinMode({ context: officeContext, platformSupported: true }), PASSKEY_MODE)
	assert.equal(resolveCheckinMode({ context: officeContext, platformSupported: false }), QR_MODE)
	assert.equal(resolveCheckinMode({ context: { enabled: false }, platformSupported: true }), QR_MODE)
	assert.equal(resolveCheckinMode({ context: null, platformSupported: true }), QR_MODE)
})

test("location is only needed off the office network", () => {
	assert.equal(needsLocation(officeContext), false)
	assert.equal(needsLocation({ on_office_network: false }), true)
})

test("office network check-in skips location and succeeds", async () => {
	const { deps, calls } = makeDeps({ getPosition: async () => assert.fail("should not ask location") })
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps })
	assert.equal(result.outcome, "success")
	assert.deepEqual(
		calls.map(([method]) => method),
		["hrms.api.passkey.begin_checkin", "hrms.api.passkey.complete_checkin"]
	)
	assert.deepEqual(calls[0][1], { log_type: "IN" })
})

test("mobile data sends the position with the begin call", async () => {
	const { deps, calls } = makeDeps()
	await runPasskeyCheckin({ logType: "OUT", context: { ...officeContext, on_office_network: false }, deps })
	assert.deepEqual(calls[0][1], { log_type: "OUT", latitude: 35.6, longitude: 139.7, accuracy: 20 })
})

test("need_location from the server retries once with a position", async () => {
	let begins = 0
	const { deps, calls } = makeDeps({
		responses: {
			"hrms.api.passkey.begin_checkin": () =>
				++begins === 1
					? { status: "need_location" }
					: { status: "ok", options: { challenge: "a" }, evidence: "gps" },
		},
	})
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps })
	assert.equal(result.outcome, "success")
	assert.equal(calls[1][1].latitude, 35.6)
})

test("location failure and presence failure lead to the QR fallback", async () => {
	const noGps = makeDeps({
		getPosition: async () => {
			throw new Error("denied")
		},
	})
	const noGpsResult = await runPasskeyCheckin({
		logType: "IN",
		context: { ...officeContext, on_office_network: false },
		deps: noGps.deps,
	})
	assert.equal(noGpsResult.outcome, "location_failed")
	const far = makeDeps({
		responses: { "hrms.api.passkey.begin_checkin": { status: "presence_unconfirmed", reason: "too_far" } },
	})
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps: far.deps })
	assert.deepEqual([result.outcome, result.reason], ["presence_unconfirmed", "too_far"])
})

test("first use registers the phone and then checks in", async () => {
	const { deps, calls } = makeDeps()
	const result = await runPasskeyCheckin({ logType: "IN", context: { ...officeContext, has_passkey: false }, deps })
	assert.equal(result.outcome, "success")
	assert.deepEqual(
		calls.map(([method]) => method.split(".").pop()),
		["register_options", "register_complete", "begin_checkin", "complete_checkin"]
	)
	assert.equal(calls[1][1].device_name, "iPhone")
})

test("invalid state during setup continues to checkin", async () => {
	const { deps, calls } = makeDeps({
		startRegistration: async () => {
			throw namedError("InvalidStateError")
		},
	})
	const result = await runPasskeyCheckin({ logType: "IN", context: { ...officeContext, has_passkey: false }, deps })
	assert.equal(result.outcome, "success")
	assert.ok(!calls.some(([method]) => method.endsWith("register_complete")))
})

test("cancelled setup and cancelled authentication go to the fallback sheet", async () => {
	const cancel = async () => {
		throw namedError("NotAllowedError")
	}
	const setup = makeDeps({ startRegistration: cancel })
	assert.deepEqual(
		await runPasskeyCheckin({ logType: "IN", context: { ...officeContext, has_passkey: false }, deps: setup.deps }),
		{ outcome: "setup_failed", kind: "cancelled" }
	)
	const auth = makeDeps({ startAuthentication: cancel })
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps: auth.deps })
	assert.equal(result.outcome, "webauthn_failed")
	assert.equal(result.kind, "cancelled")
	assert.deepEqual(result.pending, { options: { challenge: "auth" }, evidence: "office_network", createdAt: 1000 })
})

test("retry reuses fresh pending options without calling begin again", async () => {
	const { deps, calls } = makeDeps()
	const pending = { options: { challenge: "old" }, evidence: "gps", createdAt: 1000 }
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps, pending })
	assert.equal(result.outcome, "success")
	assert.deepEqual(calls.map(([method]) => method.split(".").pop()), ["complete_checkin"])
})

test("stale pending options are replaced by a new begin call", async () => {
	const { deps, calls } = makeDeps()
	const pending = { options: { challenge: "old" }, evidence: "gps", createdAt: -200000 }
	await runPasskeyCheckin({ logType: "IN", context: officeContext, deps, pending })
	assert.deepEqual(calls.map(([method]) => method.split(".").pop()), ["begin_checkin", "complete_checkin"])
})

test("server no_passkey triggers setup once", async () => {
	let begins = 0
	const { deps, calls } = makeDeps({
		responses: {
			"hrms.api.passkey.begin_checkin": () =>
				++begins === 1
					? { status: "no_passkey" }
					: { status: "ok", options: { challenge: "a" }, evidence: "office_network" },
		},
	})
	const result = await runPasskeyCheckin({ logType: "IN", context: officeContext, deps })
	assert.equal(result.outcome, "success")
	assert.equal(calls.filter(([method]) => method.endsWith("register_options")).length, 1)
})

test("server errors become readable error outcomes", async () => {
	const { deps } = makeDeps({ responses: { "hrms.api.passkey.begin_checkin": new Error("请 15 分钟后再签退") } })
	assert.deepEqual(await runPasskeyCheckin({ logType: "OUT", context: officeContext, deps }), {
		outcome: "error",
		message: "请 15 分钟后再签退",
	})
})

test("webauthn error classification", () => {
	assert.equal(classifyWebAuthnError({ name: "InvalidStateError" }), "already_registered")
	assert.equal(classifyWebAuthnError({ name: "NotAllowedError" }), "cancelled")
	assert.equal(classifyWebAuthnError({ name: "AbortError" }), "cancelled")
	assert.equal(classifyWebAuthnError(new Error("boom")), "failed")
})

test("wifi tip shows once and only for gps evidence", () => {
	const store = new Map()
	const storage = { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, v) }
	assert.equal(shouldShowWifiTip("office_network", storage), false)
	assert.equal(shouldShowWifiTip("gps", storage), true)
	assert.equal(shouldShowWifiTip("gps", storage), false)
	assert.equal(
		shouldShowWifiTip("gps", {
			getItem: () => {
				throw new Error("blocked")
			},
		}),
		false
	)
})

test("a location failure keeps its reason so the sheet can explain it", async () => {
	const { deps } = makeDeps({
		getPosition: async () => {
			throw Object.assign(new Error("denied"), { reason: "denied" })
		},
	})
	const result = await runPasskeyCheckin({
		logType: "IN",
		context: { ...officeContext, on_office_network: false },
		deps,
	})
	assert.deepEqual(result, { outcome: "location_failed", reason: "denied" })
})

test("the presence sheet explains why the location failed", () => {
	const denied = getSheetContent("presence", "ja", { locationFailed: true, locationFailureReason: "denied" })
	const timeout = getSheetContent("presence", "ja", { locationFailed: true, locationFailureReason: "timeout" })
	assert.equal(denied.body, locationFailureAdvice("denied", "ja"))
	assert.notEqual(denied.body, timeout.body)
	assert.deepEqual(denied.actions.map((a) => a.id), ["retry", "scan"])
	assert.deepEqual(getSheetContent("presence", "ja").actions.map((a) => a.id), ["scan"])
})

test("sheet content has the right actions per variant", () => {
	assert.deepEqual(getSheetContent("first_time", "zh").actions.map((a) => a.id), ["start", "scan"])
	assert.deepEqual(getSheetContent("fallback", "ja").actions.map((a) => a.id), ["retry", "resetup", "scan"])
	const presence = getSheetContent("presence", "zh", { locationLabel: "2F入口" })
	assert.deepEqual(presence.actions.map((a) => a.id), ["scan"])
	assert.match(presence.body, /2F入口/)
	assert.match(getSheetContent("presence", "en", { locationFailed: true }).body, /location/i)
	for (const variant of ["first_time", "fallback", "presence"]) {
		for (const lang of ["zh", "ja", "en"]) {
			const content = getSheetContent(variant, lang)
			assert.ok(content.title && content.actions.every((a) => a.label), `${variant}/${lang}`)
		}
	}
})

test("frappe errors are extracted from server messages", () => {
	const data = { _server_messages: JSON.stringify([JSON.stringify({ message: "请稍后再试" })]) }
	assert.equal(extractFrappeError(data), "请稍后再试")
	assert.equal(extractFrappeError({ exception: "frappe.exceptions.ValidationError: 不能打卡" }), "不能打卡")
	assert.equal(extractFrappeError({}), "")
})

test("frappe caller posts json with csrf and returns message", async () => {
	const requests = []
	const call = createFrappeCaller({
		fetchImpl: async (url, init) => {
			requests.push([url, init])
			return { ok: true, json: async () => ({ message: { status: "ok" } }) }
		},
		getCsrfToken: () => "token",
	})
	assert.deepEqual(await call("hrms.api.passkey.begin_checkin", { log_type: "IN" }), { status: "ok" })
	assert.equal(requests[0][0], "/api/method/hrms.api.passkey.begin_checkin")
	assert.equal(requests[0][1].headers["X-Frappe-CSRF-Token"], "token")
	const failing = createFrappeCaller({
		fetchImpl: async () => ({
			ok: false,
			json: async () => ({ _server_messages: JSON.stringify([JSON.stringify({ message: "不行" })]) }),
		}),
		getCsrfToken: () => "",
	})
	await assert.rejects(() => failing("x", {}), /不行/)
})

test("server errors get a sheet with retry, re-setup and the QR fallback", () => {
	const content = getSheetContent("error", "zh", { message: "打卡超时，请再试一次。" })
	assert.deepEqual(content.actions.map((a) => a.id), ["retry", "resetup", "scan"])
	assert.equal(content.body, "打卡超时，请再试一次。")
	assert.ok(getSheetContent("error", "ja").body)
})
