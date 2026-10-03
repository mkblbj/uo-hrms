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

function setupGlobalGate(t, onBlocked) {
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
	const { descriptor } = parse(read("../components/profile/ProfilePhotoGate.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const state = runInNewContext(`${script}\n;({ blocked, needsPhoto, onUploaded, recheck })`, {
		computed,
		watch: (...args) => {
			const stop = watch(...args)
			stops.push(stop)
			return stop
		},
		defineProps: () => ({ lang: "zh" }),
		defineEmits: () => (_name, value) => onBlocked(value),
		onMounted() {},
		onBeforeUnmount() {},
		status,
		pickPhotoCopy,
		toast: { success() {} },
		refreshProfilePhoto() {},
	})
	t.after(() => stops.forEach((stop) => stop()))
	return {
		...state,
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

test("the global photo gate blocks unfinished photos and releases access after a successful upload", (t) => {
	const app = setupAppGate(t, { routeName: "EmployeeChat" })
	const gate = setupGlobalGate(t, (value) => {
		app.photoGateBlocked.value = value
	})
	assert.equal(app.canUseApp.value, false)
	gate.respond(temporaryPhoto)
	assert.equal(gate.needsPhoto.value, true)
	assert.equal(app.canUseApp.value, false)
	gate.onUploaded("/files/own-photo.gif")
	assert.equal(gate.needsPhoto.value, false)
	assert.equal(app.canUseApp.value, true)
	gate.respond({ ...temporaryPhoto, has_photo: true, temporary: false })
	assert.equal(app.canUseApp.value, true)
})

test("own photos and a disabled requirement allow access on the first check", (t) => {
	for (const status of [
		{ ...temporaryPhoto, has_photo: true },
		{ ...temporaryPhoto, required: false },
	]) {
		const app = setupAppGate(t)
		const gate = setupGlobalGate(t, (value) => {
			app.photoGateBlocked.value = value
		})
		gate.respond(status)
		assert.equal(app.canUseApp.value, true)
	}
})

test("a failed photo status check stays locked and retry checks the actual status", (t) => {
	const app = setupAppGate(t)
	const gate = setupGlobalGate(t, (value) => {
		app.photoGateBlocked.value = value
	})
	gate.fail()
	assert.equal(app.canUseApp.value, false)
	gate.recheck()
	gate.respond({ ...temporaryPhoto, has_photo: true })
	assert.equal(app.canUseApp.value, true)
})

test("a locked app rechecks server state when the requirement is lifted or another device uploads", (t) => {
	for (const next of [
		{ ...temporaryPhoto, required: false },
		{ ...temporaryPhoto, has_photo: true },
	]) {
		const app = setupAppGate(t)
		const gate = setupGlobalGate(t, (value) => {
			app.photoGateBlocked.value = value
		})
		gate.respond(temporaryPhoto)
		assert.equal(app.canUseApp.value, false)
		const request = gate.recheck()
		assert.ok(request instanceof Promise)
		gate.respond(next)
		assert.equal(app.canUseApp.value, true)
	}
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

function setupSheet(props, uploadImpl = async () => "/files/own-photo.jpg") {
	const emitted = []
	const { descriptor } = parse(read("../components/profile/ProfilePhotoSheet.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const state = runInNewContext(
		`${script}\n;({ canDismiss: typeof canDismiss === 'function' ? canDismiss : () => true, close, upload, editorRef, errorMessage })`,
		{
			computed,
			ref,
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
	return { ...state, emitted }
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

function setupAppGate(
	t,
	{ user = "employee@example.com", routeName = "Home", linked = true } = {}
) {
	const stops = []
	const session = reactive({ user, isLoggedIn: Boolean(user) })
	const route = reactive({ name: routeName })
	const employeeResource = reactive({ data: linked ? { user_id: user } : null })
	const { descriptor } = parse(read("../App.vue"))
	const script = descriptor.scriptSetup.content.replace(/import[\s\S]*?from ["'][^"']+["']/g, "")
	const state = runInNewContext(
		`${script}\n;({ canUseApp: typeof canUseApp !== 'undefined' ? canUseApp : computed(() => true), photoGateBlocked: typeof photoGateBlocked !== 'undefined' ? photoGateBlocked : ref(false) })`,
		{
			computed,
			ref,
			watch: (...args) => {
				const stop = watch(...args)
				stops.push(stop)
				return stop
			},
			onMounted() {},
			useTheme() {},
			useRoute: () => route,
			resolveHomeLanguage: () => "zh",
			session,
			employeeResource,
			window: {},
		}
	)
	t.after(() => stops.forEach((stop) => stop()))
	return { ...state, session, route }
}

test("all employee routes stay locked until the global photo check allows access", (t) => {
	for (const routeName of ["Home", "Profile", "EmployeeChat", "AttendanceDashboard"]) {
		const app = setupAppGate(t, { routeName })
		assert.equal(app.canUseApp.value, false, routeName)
		app.photoGateBlocked.value = false
		assert.equal(app.canUseApp.value, true, routeName)
		app.photoGateBlocked.value = true
		assert.equal(app.canUseApp.value, false, routeName)
	}
})

test("photo enforcement leaves login, password recovery and invalid employee pages available", (t) => {
	for (const routeName of ["Login", "ForgotPassword", "InvalidEmployee"]) {
		assert.equal(setupAppGate(t, { routeName }).canUseApp.value, true)
	}
	assert.equal(setupAppGate(t, { user: null }).canUseApp.value, true)
	assert.equal(setupAppGate(t, { linked: false }).canUseApp.value, true)
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
