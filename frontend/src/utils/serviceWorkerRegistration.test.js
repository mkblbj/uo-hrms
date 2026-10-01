import test from "node:test"
import assert from "node:assert/strict"

import {
	getTokenWithServiceWorker,
	waitForActiveServiceWorker,
} from "./serviceWorkerRegistration.js"

test("push waits for a newly installed service worker before subscribing", async () => {
	const worker = new EventTarget()
	worker.state = "installing"
	const registration = { active: null, installing: worker }
	let settled = false
	const ready = waitForActiveServiceWorker(registration).then(() => {
		settled = true
	})

	await Promise.resolve()
	assert.equal(settled, false)

	registration.active = worker
	worker.state = "activated"
	worker.dispatchEvent(new Event("statechange"))
	await ready
	assert.equal(settled, true)
})

test("push retries once with a fresh registration when WebKit loses the old one", async () => {
	let oldRegistrationRemoved = false
	const stale = {
		active: {},
		async unregister() {
			oldRegistrationRemoved = true
		},
	}
	const fresh = { active: {} }
	const registrations = []
	const result = await getTokenWithServiceWorker({
		registration: stale,
		register: async () => {
			assert.equal(oldRegistrationRemoved, true)
			return fresh
		},
		getToken: async (current) => {
			registrations.push(current)
			if (current === stale) {
				throw new DOMException(
					"Getting push subscription requires a service worker",
					"InvalidStateError"
				)
			}
			return "new-token"
		},
	})

	assert.deepEqual(registrations, [stale, fresh])
	assert.deepEqual(result, { token: "new-token", registration: fresh })
})

test("push does not retry unrelated subscription errors", async () => {
	const failure = new Error("relay unavailable")
	let registerCalls = 0
	await assert.rejects(
		getTokenWithServiceWorker({
			registration: { active: {} },
			register: async () => {
				registerCalls++
			},
			getToken: async () => {
				throw failure
			},
		}),
		(error) => error === failure
	)
	assert.equal(registerCalls, 0)
})
