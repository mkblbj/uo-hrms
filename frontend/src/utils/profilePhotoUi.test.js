import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { runInNewContext } from "node:vm"
import { parse } from "@vue/compiler-sfc"
import { computed, reactive, ref, watch } from "vue"

import {
	PHOTO_STATUS_METHOD,
	getPromptCardContent,
	getReminderContent,
	pickPhotoCopy,
} from "./profilePhoto.js"

const dir = path.dirname(fileURLToPath(import.meta.url))
const read = (relative) => fs.readFileSync(path.resolve(dir, relative), "utf8")

test("home shows the photo reminder right under the notification prompt", () => {
	const source = read("../components/CheckInPanel.vue")
	assert.match(
		source,
		/<PushNotificationPrompt \/>\s*<ProfilePhotoReminder :lang="currentLanguage" \/>/
	)
})

const temporaryPhoto = {
	required: true,
	has_photo: false,
	temporary: true,
	photo: "/files/landscape-avatar-test.png",
	deadline: "2026-10-06",
	overdue: false,
}

function setupReminderGate(t, { now = () => 0 } = {}) {
	const stops = []
	let resolveRequest
	let rejectRequest
	const status = reactive({
		data: null,
		loading: false,
		error: null,
		abort() {},
		reset() {
			this.data = null
			this.error = null
			this.loading = false
		},
		setData(data) {
			this.data = data
		},
		reload() {
			this.loading = true
			this.error = null
			return new Promise((resolve, reject) => {
				resolveRequest = resolve
				rejectRequest = reject
			})
		},
	})
	// 每个提醒入口都是一次新打开的应用：提醒状态各自独立
	const photoReminder = reactive({ open: false, snoozeDelay: 0 })
	const { descriptor } = parse(read("../components/profile/ProfilePhotoGate.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const state = runInNewContext(
		`${script}\n;({ needsPhoto, onSnooze, onUploaded, onVisibilityChange })`,
		{
			computed,
			watch: (...args) => {
				const stop = watch(...args)
				stops.push(stop)
				return stop
			},
			defineProps: () => ({ lang: "zh" }),
			onMounted() {},
			onBeforeUnmount() {},
			status,
			photoReminder,
			openPhotoReminder(snoozeDelay = 0) {
				photoReminder.snoozeDelay = snoozeDelay
				photoReminder.open = true
			},
			pickPhotoCopy,
			toast: { success() {} },
			refreshProfilePhoto() {},
			document: { visibilityState: "visible" },
			Date: { now },
		}
	)
	t.after(() => stops.forEach((stop) => stop()))
	return {
		...state,
		photoReminder,
		respond(data) {
			status.data = data
			status.loading = false
			resolveRequest(data)
		},
		fail() {
			status.error = new Error("offline")
			status.loading = false
			rejectRequest(status.error)
		},
	}
}

test("a missing photo opens the reminder with a 60 second wait every time the app opens", (t) => {
	const gate = setupReminderGate(t)
	assert.equal(gate.photoReminder.open, false)
	gate.respond(temporaryPhoto)
	assert.deepEqual([gate.photoReminder.open, gate.photoReminder.snoozeDelay], [true, 60])
	gate.onSnooze()
	assert.equal(gate.photoReminder.open, false)
	const nextLaunch = setupReminderGate(t)
	nextLaunch.respond(temporaryPhoto)
	assert.deepEqual([nextLaunch.photoReminder.open, nextLaunch.photoReminder.snoozeDelay], [true, 60])
})

test("own photos, a disabled requirement or a failed check open no reminder", (t) => {
	for (const status of [
		{ ...temporaryPhoto, has_photo: true, temporary: false },
		{ ...temporaryPhoto, required: false },
	]) {
		const gate = setupReminderGate(t)
		gate.respond(status)
		assert.equal(gate.photoReminder.open, false)
	}
	const failed = setupReminderGate(t)
	failed.fail()
	assert.equal(failed.photoReminder.open, false)
})

test("after skipping, coming back to the app reminds again only after 10 minutes", (t) => {
	const clock = { now: 1_000_000 }
	const gate = setupReminderGate(t, { now: () => clock.now })
	gate.respond(temporaryPhoto)
	gate.onSnooze()
	clock.now += 9 * 60 * 1000
	gate.onVisibilityChange()
	assert.equal(gate.photoReminder.open, false)
	clock.now += 2 * 60 * 1000
	gate.onVisibilityChange()
	assert.deepEqual([gate.photoReminder.open, gate.photoReminder.snoozeDelay], [true, 60])
})

test("uploading a photo closes the reminder", (t) => {
	const gate = setupReminderGate(t)
	gate.respond(temporaryPhoto)
	gate.onUploaded("/files/own-photo.jpg")
	assert.equal(gate.needsPhoto.value, false)
	assert.equal(gate.photoReminder.open, false)
})

test("the home card opens the reminder without the wait", () => {
	const opened = []
	const { descriptor } = parse(read("../components/home/ProfilePhotoReminder.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const card = runInNewContext(`${script}\n;({ showCard, checkProfilePhoto })`, {
		computed,
		defineProps: () => ({ lang: "zh" }),
		status: reactive({ data: temporaryPhoto, reload: async () => temporaryPhoto }),
		getPromptCardContent,
		openPhotoReminder: (snoozeDelay = 0) => opened.push(snoozeDelay),
	})
	assert.equal(card.showCard.value, true)
	card.checkProfilePhoto()
	assert.deepEqual(opened, [0])
})

test("sheet offers camera and library, cannot be dismissed by tapping outside", () => {
	const source = read("../components/profile/ProfilePhotoSheet.vue")
	assert.match(source, /:backdrop-dismiss="mandatory"/)
	assert.equal((source.match(/type="file"/g) || []).length, 2)
	assert.equal((source.match(/accept="image\/\*"/g) || []).length, 2)
	assert.match(source, /capture="user"/)
	assert.match(source, /uploadProfilePhoto/)
	assert.match(source, /<ProfilePhotoEditor/)
	// 提醒只保留一句话，不再列用途、要求、承诺
	assert.doesNotMatch(source, /photo-sheet-section/)
	// 隐藏的选图框不能用 display:none
	assert.doesNotMatch(source, /\.photo-sheet-input\s*{[^}]*display:\s*none/)
})

function setupSheet(props, uploadImpl = async () => "/files/own-photo.jpg", { now = () => 0 } = {}) {
	const emitted = []
	const timers = []
	const { descriptor } = parse(read("../components/profile/ProfilePhotoSheet.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const state = runInNewContext(
		`${script}\n;({ canDismiss: typeof canDismiss === 'function' ? canDismiss : () => true, close, upload, editorRef, errorMessage, remaining: typeof remaining !== 'undefined' ? remaining : ref(0) })`,
		{
			computed,
			ref,
			watch,
			Date: { now },
			setInterval: (fn) => timers.push(fn),
			clearInterval() {},
			defineProps: () => props,
			defineEmits: () => (name, value) => emitted.push({ name, value }),
			onBeforeUnmount() {},
			getReminderContent,
			pickPhotoCopy,
			preparePhotoUpload: async () => ({ blob: new Blob(["photo"]), crop: null }),
			uploadProfilePhoto: uploadImpl,
			defineExpose() {},
		}
	)
	state.editorRef.value = {}
	return { ...state, emitted, tick: () => timers.forEach((fn) => fn()) }
}

test("mandatory photo sheet refuses every dismiss action until the upload succeeds", async () => {
	const sheet = setupSheet({
		mandatory: true,
		isOpen: true,
		mode: "reminder",
		lang: "zh",
		status: temporaryPhoto,
	})
	assert.equal(sheet.canDismiss(undefined, "backdrop"), false)
	assert.equal(sheet.canDismiss(undefined, "cancel"), false)
	sheet.close("snooze")
	assert.equal(sheet.emitted.length, 0)
	await sheet.upload()
	assert.equal(sheet.emitted[0].name, "uploaded")
	assert.equal(sheet.canDismiss(), true)
})

test("a failed mandatory upload keeps the sheet locked and shows its error", async () => {
	const sheet = setupSheet(
		{ mandatory: true, isOpen: true, mode: "reminder", lang: "zh", status: temporaryPhoto },
		async () => {
			throw new Error("上传失败，请重试。")
		}
	)
	await sheet.upload()
	assert.equal(sheet.emitted.length, 0)
	assert.equal(sheet.canDismiss(), false)
	assert.equal(sheet.errorMessage.value, "上传失败，请重试。")
})

test("normal profile photo changes can still be cancelled", () => {
	const sheet = setupSheet({
		mandatory: false,
		isOpen: true,
		mode: "change",
		lang: "zh",
		status: null,
	})
	assert.equal(sheet.canDismiss(), true)
	sheet.close("cancel")
	assert.equal(sheet.emitted[0].name, "cancel")
})

test("the later button only works after its 60 second countdown", () => {
	const clock = { now: 0 }
	const sheet = setupSheet(
		{ mandatory: false, isOpen: true, mode: "reminder", lang: "zh", status: temporaryPhoto, snoozeDelay: 60 },
		undefined,
		{ now: () => clock.now }
	)
	assert.equal(sheet.remaining.value, 60)
	assert.equal(sheet.canDismiss(undefined, "cancel"), false)
	sheet.close("snooze")
	assert.equal(sheet.emitted.length, 0)
	clock.now = 59_500
	sheet.tick()
	assert.equal(sheet.remaining.value, 1)
	clock.now = 60_000
	sheet.tick()
	assert.equal(sheet.remaining.value, 0)
	assert.equal(sheet.canDismiss(undefined, "cancel"), true)
	sheet.close("snooze")
	assert.equal(sheet.emitted[0].name, "snooze")
})

test("a reminder opened from the home card can be closed at once", () => {
	const sheet = setupSheet({
		mandatory: false,
		isOpen: true,
		mode: "reminder",
		lang: "zh",
		status: temporaryPhoto,
		snoozeDelay: 0,
	})
	assert.equal(sheet.remaining.value, 0)
	sheet.close("snooze")
	assert.equal(sheet.emitted[0].name, "snooze")
})

test("editor is a round frame with drag, pinch and a zoom slider", () => {
	const source = read("../components/profile/ProfilePhotoEditor.vue")
	for (const needle of [
		"@pointerdown",
		"@pointermove",
		"@pointerup",
		"@pointercancel",
		'type="range"',
		"touch-action: none",
		"border-radius: 50%",
		'"image/jpeg"',
		"cropRect",
		"defineExpose({ exportBlob, getCrop:",
	]) {
		assert.ok(source.includes(needle), needle)
	}
})

test("profile page lets people change their photo", () => {
	const source = read("../views/Profile.vue")
	assert.match(source, /<ProfilePhotoSheet[\s\S]*mode="change"/)
	assert.match(source, /isPhotoSheetOpen = true/)
	assert.match(source, /refreshProfilePhoto/)
})

test("wall display passes its key when asking for recent check-ins", () => {
	const source = read("../../../hrms/www/qr_display.html")
	assert.match(source, /get_recent_checkins\?[^`]*&key=\$\{encodeURIComponent\(DISPLAY_KEY\)\}/)
})

test("photo copy has no technical wording", () => {
	const status = { required: true, has_photo: false, deadline: "2026-10-10", overdue: false }
	const texts = []
	for (const lang of ["zh", "ja", "en"]) {
		for (const variant of [status, { ...status, photo: "/files/a.png", temporary: true }]) {
			const reminder = getReminderContent(variant, lang)
			texts.push(reminder.title, reminder.lead)
		}
		texts.push(
			...Object.values(getPromptCardContent(status, lang)).filter((v) => typeof v === "string")
		)
		for (const key of ["editHint", "readFailed", "tooSmall", "uploadFailed", "uploaded"]) {
			texts.push(pickPhotoCopy(key, lang))
		}
	}
	for (const text of texts) {
		assert.doesNotMatch(text, /EXIF|JPEG|API|CSRF|512|px|\bURL\b|HTTP|服务器|サーバー/i, text)
	}
})
