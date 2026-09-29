import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import { getPromptCardContent, getReminderContent, pickPhotoCopy } from "./profilePhoto.js"

const dir = path.dirname(fileURLToPath(import.meta.url))
const read = (relative) => fs.readFileSync(path.resolve(dir, relative), "utf8")

test("home shows the photo reminder right under the notification prompt", () => {
	const source = read("../components/CheckInPanel.vue")
	assert.match(
		source,
		/<PushNotificationPrompt \/>\s*<ProfilePhotoReminder :lang="currentLanguage" \/>/
	)
})

test("reminder pops up on open and on return, and respects the snooze", () => {
	const source = read("../components/home/ProfilePhotoReminder.vue")
	for (const needle of [
		"PHOTO_STATUS_METHOD",
		"shouldShowPhotoReminder",
		"readSnoozedAt",
		"writeSnoozedAt",
		"visibilitychange",
		"onIonViewDidEnter",
		'mode="reminder"',
		"refreshProfilePhoto",
		":current-photo=\"status.data?.photo || ''\"",
	]) {
		assert.ok(source.includes(needle), needle)
	}
})

test("sheet offers camera and library, cannot be dismissed by tapping outside", () => {
	const source = read("../components/profile/ProfilePhotoSheet.vue")
	assert.match(source, /:backdrop-dismiss="false"/)
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
		"defineExpose({ exportBlob })",
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
