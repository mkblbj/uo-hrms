import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

import FrappePushNotification from "../../public/frappe-push-notification.js"
import { resolvePushPromptState } from "./pushNotifications.js"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const promptPath = path.resolve(currentDir, "../components/home/PushNotificationPrompt.vue")
const panelPath = path.resolve(currentDir, "../components/CheckInPanel.vue")
const settingsPath = path.resolve(currentDir, "../views/AppSettings.vue")

test("guides iPhone users to install before requesting push permission", () => {
	assert.equal(
		resolvePushPromptState({
			isIos: true,
			isStandalone: false,
			permission: "default",
			hasToken: false,
			supported: false,
		}),
		"install"
	)
})

test("shows the enable action until permission and token are both ready", () => {
	assert.equal(
		resolvePushPromptState({
			isIos: true,
			isStandalone: true,
			permission: "default",
			hasToken: false,
			supported: true,
		}),
		"prompt"
	)
	assert.equal(
		resolvePushPromptState({
			isIos: false,
			isStandalone: false,
			permission: "granted",
			hasToken: false,
			supported: true,
		}),
		"prompt"
	)
})

test("keeps denied guidance visible and hides completed or unsupported prompts", () => {
	assert.equal(
		resolvePushPromptState({
			permission: "denied",
			hasToken: false,
			supported: true,
		}),
		"denied"
	)
	assert.equal(
		resolvePushPromptState({
			permission: "granted",
			hasToken: true,
			supported: true,
		}),
		"enabled"
	)
	assert.equal(
		resolvePushPromptState({
			permission: "default",
			hasToken: false,
			supported: false,
		}),
		"hidden"
	)
})

test("notification enabled state requires both system permission and a local token", () => {
	const values = new Map([["firebase_token_hrms", "stored-token"]])
	const originalNotification = globalThis.Notification
	const originalStorage = globalThis.localStorage
	globalThis.localStorage = {
		getItem(key) {
			return values.get(key) ?? null
		},
	}
	globalThis.Notification = { permission: "denied" }

	try {
		const client = new FrappePushNotification("hrms")
		assert.equal(client.isNotificationEnabled(), false)
		globalThis.Notification.permission = "granted"
		assert.equal(client.isNotificationEnabled(), true)
		values.delete("firebase_token_hrms")
		assert.equal(client.isNotificationEnabled(), false)
	} finally {
		globalThis.Notification = originalNotification
		globalThis.localStorage = originalStorage
	}
})

test("home uses a persistent accessible push activation card", () => {
	assert.equal(fs.existsSync(promptPath), true, "push activation card should exist")
	const source = fs.readFileSync(promptPath, "utf8")
	assert.match(source, /<section/)
	assert.match(source, /aria-live="polite"/)
	assert.match(source, /シフト通知を有効にする/)
	assert.match(source, /通知を有効にする/)
	assert.match(source, /:loading="isLoading"/)
	assert.match(source, /min-height:\s*44px/)
	assert.match(source, /resolvePushPromptState/)
	assert.match(source, /enableNotification/)
	assert.match(source, /visibilitychange/)
	assert.match(source, /onIonViewWillEnter/)
	assert.doesNotMatch(source, /error\?\.message/)
	assert.doesNotMatch(source, /<Dialog|<ion-modal/)
})

test("push activation is the first card in the home content", () => {
	const source = fs.readFileSync(panelPath, "utf8")
	const saleBannerIndex = source.indexOf('class="home-sale-banner')
	const preferenceBannerIndex = source.indexOf("<RosterPreferenceBanner")
	const heroIndex = source.indexOf("<HomeHeroCard")
	const promptIndex = source.indexOf("<PushNotificationPrompt")
	const summaryIndex = source.indexOf("<HomeSummaryCard")
	assert.notEqual(promptIndex, -1)
	assert.notEqual(preferenceBannerIndex, -1)
	assert.ok(promptIndex < saleBannerIndex)
	assert.ok(promptIndex < preferenceBannerIndex)
	assert.ok(promptIndex < heroIndex)
	assert.ok(promptIndex < summaryIndex)
})

test("settings refreshes the real push state whenever the page becomes active", () => {
	const source = fs.readFileSync(settingsPath, "utf8")
	assert.match(source, /onIonViewWillEnter/)
	assert.match(
		source,
		/pushNotificationState\.value\s*=\s*window\.frappePushNotification\?\.isNotificationEnabled\(\)/
	)
})
