import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import {
	FRONTEND_VERSION_PATH,
	createFrontendVersionChecker,
	fetchFrontendVersion,
	hasNewFrontendVersion,
	requestServiceWorkerUpdate,
} from "./frontendVersion.js"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(currentDir, "../..")
const appPath = path.resolve(currentDir, "../App.vue")
const appUpdatePromptPath = path.resolve(currentDir, "../components/AppUpdatePrompt.vue")
const viteConfigPath = path.resolve(frontendRoot, "vite.config.js")

test("fetchFrontendVersion requests the manifest without using browser cache", async () => {
	const calls = []
	const version = await fetchFrontendVersion({
		now: () => 12345,
		fetchImpl: async (url, options) => {
			calls.push({ url, options })
			return {
				ok: true,
				json: async () => ({ version: "1.0.0-uo-2026", buildTime: "2026-05-14T00:00:00.000Z" }),
			}
		},
	})

	assert.deepEqual(version, {
		version: "1.0.0-uo-2026",
		buildTime: "2026-05-14T00:00:00.000Z",
	})
	assert.equal(calls.length, 1)
	assert.equal(calls[0].url, `${FRONTEND_VERSION_PATH}?t=12345`)
	assert.deepEqual(calls[0].options, {
		cache: "no-store",
		credentials: "same-origin",
	})
})

test("fetchFrontendVersion returns null for failed or malformed responses", async () => {
	assert.equal(
		await fetchFrontendVersion({
			fetchImpl: async () => ({ ok: false, json: async () => ({ version: "next" }) }),
		}),
		null
	)
	assert.equal(
		await fetchFrontendVersion({
			fetchImpl: async () => ({ ok: true, json: async () => ({ buildTime: "missing version" }) }),
		}),
		null
	)
	assert.equal(
		await fetchFrontendVersion({
			fetchImpl: async () => {
				throw new Error("network unavailable")
			},
		}),
		null
	)
})

test("hasNewFrontendVersion compares the current build with the remote manifest", () => {
	assert.equal(
		hasNewFrontendVersion({
			currentVersion: { version: "current" },
			remoteVersion: { version: "current" },
		}),
		false
	)
	assert.equal(
		hasNewFrontendVersion({
			currentVersion: { version: "current" },
			remoteVersion: { version: "next" },
		}),
		true
	)
	assert.equal(
		hasNewFrontendVersion({ currentVersion: { version: "current" }, remoteVersion: null }),
		false
	)
})

test("createFrontendVersionChecker returns update state without throwing on fetch errors", async () => {
	const checker = createFrontendVersionChecker({
		currentVersion: { version: "current" },
		fetchVersion: async () => ({ version: "next", buildTime: "later" }),
	})

	assert.deepEqual(await checker.check(), {
		currentVersion: { version: "current" },
		remoteVersion: { version: "next", buildTime: "later" },
		updateAvailable: true,
	})

	const failingChecker = createFrontendVersionChecker({
		currentVersion: { version: "current" },
		fetchVersion: async () => {
			throw new Error("offline")
		},
	})

	assert.deepEqual(await failingChecker.check(), {
		currentVersion: { version: "current" },
		remoteVersion: null,
		updateAvailable: false,
	})
})

test("requestServiceWorkerUpdate asks the active registration to update", async () => {
	let updateCalls = 0
	const result = await requestServiceWorkerUpdate({
		serviceWorker: {
			getRegistration: async () => ({
				update: async () => {
					updateCalls += 1
				},
			}),
		},
	})

	assert.equal(result, true)
	assert.equal(updateCalls, 1)
	assert.equal(await requestServiceWorkerUpdate({ serviceWorker: null }), false)
})

test("requestServiceWorkerUpdate can use an existing stored registration", async () => {
	let updateCalls = 0
	const result = await requestServiceWorkerUpdate({
		serviceWorkerRegistration: {
			update: async () => {
				updateCalls += 1
			},
		},
		serviceWorker: null,
	})

	assert.equal(result, true)
	assert.equal(updateCalls, 1)
})

test("AppUpdatePrompt wires foreground checks and user-triggered reload", () => {
	const source = fs.readFileSync(appUpdatePromptPath, "utf8")

	assert.match(source, /createFrontendVersionChecker/)
	assert.match(source, /requestServiceWorkerUpdate/)
	assert.match(source, /visibilitychange/)
	assert.match(source, /addEventListener\("focus"/)
	assert.match(source, /addEventListener\("online"/)
	assert.match(source, /setInterval/)
	assert.match(source, /window\.location\.reload\(\)/)
})

test("App mounts the global update prompt", () => {
	const source = fs.readFileSync(appPath, "utf8")

	assert.match(source, /AppUpdatePrompt/)
	assert.match(source, /<AppUpdatePrompt \/>/)
})

test("Vite emits a runtime version manifest and build constants", () => {
	const source = fs.readFileSync(viteConfigPath, "utf8")

	assert.match(source, /frontend-version\.json/)
	assert.match(source, /__HRMS_FRONTEND_VERSION__/)
	assert.match(source, /__HRMS_FRONTEND_BUILD_TIME__/)
	assert.match(source, /emitFrontendVersionPlugin/)
})
