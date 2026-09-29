import test from "node:test"
import assert from "node:assert/strict"

import {
	PHOTO_MIN_SIDE,
	PHOTO_OUTPUT_SIZE,
	PHOTO_REMINDER_SNOOZE_MS,
	PHOTO_REMINDER_STORAGE_KEY,
	clampOffset,
	cropRect,
	formatDeadline,
	getPromptCardContent,
	getReminderContent,
	maxZoomFor,
	outputSizeFor,
	pickPhotoCopy,
	readSnoozedAt,
	shouldShowPhotoReminder,
	uploadProfilePhoto,
	writeSnoozedAt,
} from "./profilePhoto.js"

const missing = { required: true, has_photo: false, deadline: null, overdue: false }

function memoryStorage() {
	const data = new Map()
	return {
		getItem: (key) => (data.has(key) ? data.get(key) : null),
		setItem: (key, value) => data.set(key, String(value)),
		data,
	}
}

const brokenStorage = {
	getItem() {
		throw new Error("blocked")
	},
	setItem() {
		throw new Error("blocked")
	},
}

test("copy is picked by language and falls back to Chinese", () => {
	assert.equal(pickPhotoCopy("title", "zh"), "请设置头像")
	assert.equal(pickPhotoCopy("title", "ja"), "プロフィール写真の設定")
	assert.equal(pickPhotoCopy("title", "fr"), "请设置头像")
	assert.equal(pickPhotoCopy("deadline", "zh", "10月10日"), "请在 10月10日 前完成")
})

test("deadline is shown as month and day", () => {
	assert.equal(formatDeadline("2026-10-05", "zh"), "10月5日")
	assert.equal(formatDeadline("2026-10-05", "ja"), "10月5日")
	assert.equal(formatDeadline("2026-10-05", "en"), "Oct 5")
	assert.equal(formatDeadline(null, "zh"), "")
	assert.equal(formatDeadline("0001-01-01", "zh"), "")
})

test("reminder shows only when required and missing, and respects a recent snooze", () => {
	const now = 1_800_000_000_000
	assert.equal(shouldShowPhotoReminder(missing, { now }), true)
	assert.equal(shouldShowPhotoReminder({ ...missing, required: false }, { now }), false)
	assert.equal(shouldShowPhotoReminder({ ...missing, has_photo: true }, { now }), false)
	assert.equal(shouldShowPhotoReminder(null, { now }), false)
	assert.equal(shouldShowPhotoReminder(missing, { now, snoozedAt: now - 60_000 }), false)
	assert.equal(
		shouldShowPhotoReminder(missing, { now, snoozedAt: now - PHOTO_REMINDER_SNOOZE_MS }),
		true
	)
	// 手机时间往回调过，也照样提醒
	assert.equal(shouldShowPhotoReminder(missing, { now, snoozedAt: now + 60_000 }), true)
})

test("snooze time is stored per device and survives blocked storage", () => {
	const storage = memoryStorage()
	assert.equal(readSnoozedAt(storage), null)
	writeSnoozedAt(storage, 1234)
	assert.equal(storage.data.get(PHOTO_REMINDER_STORAGE_KEY), "1234")
	assert.equal(readSnoozedAt(storage), 1234)
	storage.setItem(PHOTO_REMINDER_STORAGE_KEY, "garbage")
	assert.equal(readSnoozedAt(storage), null)
	assert.equal(readSnoozedAt(brokenStorage), null)
	assert.doesNotThrow(() => writeSnoozedAt(brokenStorage, 1))
	assert.equal(readSnoozedAt(undefined), null)
})

test("reminder is a short note with the deadline", () => {
	assert.deepEqual(getReminderContent({ ...missing, deadline: "2026-10-10" }, "zh"), {
		title: "请设置头像",
		deadline: "请在 10月10日 前完成",
		overdue: false,
		lead: "系统更新，需要每个人设置一张头像（请用本人照片），1 分钟就好。",
	})

	const overdue = getReminderContent({ ...missing, deadline: "2026-10-10", overdue: true }, "ja")
	assert.equal(overdue.overdue, true)
	assert.match(overdue.deadline, /過ぎています/)

	assert.equal(getReminderContent(missing, "zh").deadline, "")
})

test("reminder wording stays short", () => {
	assert.ok(getReminderContent(missing, "zh").lead.length <= 40)
	assert.ok(getReminderContent(missing, "ja").lead.length <= 45)
	assert.ok(getReminderContent(missing, "ja").title.length <= 12)
	assert.ok(getPromptCardContent(missing, "zh").message.length <= 20)
})

test("home card nudges with or without a deadline", () => {
	assert.deepEqual(getPromptCardContent(missing, "zh"), {
		title: "还没有设置头像",
		message: "系统更新，需要设置一张头像。",
		action: "去设置",
		overdue: false,
	})
	assert.equal(
		getPromptCardContent({ ...missing, deadline: "2026-10-10" }, "zh").message,
		"请在 10月10日 前设置。"
	)
	const overdue = getPromptCardContent({ ...missing, deadline: "2026-10-10", overdue: true }, "zh")
	assert.equal(overdue.overdue, true)
	assert.match(overdue.message, /已过截止日期/)
})

test("crop keeps the image covering the circle", () => {
	const base = { width: 400, height: 300, viewport: 300, zoom: 1 }
	assert.deepEqual(clampOffset({ ...base, x: 500, y: 500 }), { x: 50, y: 0 })
	assert.deepEqual(clampOffset({ ...base, x: -500, y: 0 }), { x: -50, y: 0 })
	assert.deepEqual(clampOffset({ ...base, zoom: 2, x: 0, y: -900 }), { x: 0, y: -150 })
})

test("crop rectangle follows zoom and drag", () => {
	const base = { width: 400, height: 300, viewport: 300 }
	assert.deepEqual(cropRect({ ...base, zoom: 1, x: 0, y: 0 }), { sx: 50, sy: 0, size: 300 })
	// 图往右拖到底，看到的是最左边
	assert.deepEqual(cropRect({ ...base, zoom: 1, x: 50, y: 0 }), { sx: 0, sy: 0, size: 300 })
	assert.deepEqual(cropRect({ ...base, zoom: 2, x: 0, y: 0 }), { sx: 125, sy: 75, size: 150 })
	// 屏幕上取景框 150 像素宽，原图 3000 像素时要换算回原图坐标
	assert.deepEqual(cropRect({ width: 3000, height: 4000, viewport: 150, zoom: 1, x: 0, y: 0 }), {
		sx: 0,
		sy: 500,
		size: 3000,
	})
})

test("zoom stops before the crop gets smaller than the minimum photo", () => {
	assert.equal(maxZoomFor(4032, 3024), 4)
	assert.equal(maxZoomFor(300, 256), 2)
	assert.equal(maxZoomFor(100, 100), 1)
})

test("output is at most 512 and never below the minimum", () => {
	assert.equal(outputSizeFor(3000), PHOTO_OUTPUT_SIZE)
	assert.equal(outputSizeFor(300.4), 300)
	assert.equal(outputSizeFor(90), PHOTO_MIN_SIDE)
})

test("upload posts the photo with the CSRF token and returns its address", async () => {
	const calls = []
	const fetchImpl = async (url, options) => {
		calls.push({ url, options })
		return { ok: true, status: 200, json: async () => ({ message: { photo: "/files/p.jpg" } }) }
	}
	const photo = await uploadProfilePhoto(new Blob(["x"], { type: "image/jpeg" }), {
		fetchImpl,
		csrfToken: "token-1",
	})
	assert.equal(photo, "/files/p.jpg")
	assert.equal(calls[0].url, "/api/method/hrms.api.profile_photo.upload_my_photo")
	assert.equal(calls[0].options.method, "POST")
	assert.equal(calls[0].options.headers["X-Frappe-CSRF-Token"], "token-1")
	assert.ok(calls[0].options.body instanceof FormData)
	assert.ok(calls[0].options.body.get("file"))
})

test("upload failures carry the server message when there is one", async () => {
	const serverMessage = JSON.stringify([
		JSON.stringify({ message: "照片太小了，请换一张更清晰的。" }),
	])
	const rejecting = async () => ({
		ok: false,
		status: 417,
		json: async () => ({ _server_messages: serverMessage }),
	})
	await assert.rejects(
		uploadProfilePhoto(new Blob(["x"]), { fetchImpl: rejecting, csrfToken: "t" }),
		(error) => error.message === "照片太小了，请换一张更清晰的。" && error.status === 417
	)
	const broken = async () => ({
		ok: false,
		status: 502,
		json: async () => {
			throw new Error("not json")
		},
	})
	await assert.rejects(
		uploadProfilePhoto(new Blob(["x"]), { fetchImpl: broken, csrfToken: "t" }),
		(error) => error.message === "" && error.status === 502
	)
})
