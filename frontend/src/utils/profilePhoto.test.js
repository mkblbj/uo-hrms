import test from "node:test"
import assert from "node:assert/strict"

import {
	PHOTO_MIN_SIDE,
	PHOTO_OUTPUT_SIZE,
	clampOffset,
	cropRect,
	formatDeadline,
	getPromptCardContent,
	getReminderContent,
	maxZoomFor,
	nextDay,
	outputSizeFor,
	pickPhotoCopy,
	uploadProfilePhoto,
} from "./profilePhoto.js"

const missing = { required: true, has_photo: false, deadline: null, overdue: false }
const temporary = {
	required: true,
	has_photo: false,
	temporary: true,
	photo: "/files/landscape-avatar-test.png",
	deadline: "2026-10-06",
	overdue: false,
}
const ZH_CHANGE =
	"因系统更新，自10月7日起，登录需使用您自行设置的头像。当前头像为系统临时生成，请最迟于10月6日完成更换。逾期将暂时无法登录。给您带来不便，敬请谅解。"
const JA_CHANGE =
	"システム更新により、10月7日以降のログインには、ご自身で設定したプロフィール画像が必要になります。現在の画像はシステムが仮に生成したものです。10月6日までに変更をお願いいたします。未変更の場合、一時的にログインできなくなります。ご不便をおかけしますが、ご理解のほどお願いいたします。"

test("copy is picked by language and falls back to Chinese", () => {
	assert.equal(pickPhotoCopy("titleChange", "zh"), "请更换头像")
	assert.equal(pickPhotoCopy("titleChange", "ja"), "プロフィール画像の変更")
	assert.equal(pickPhotoCopy("titleChange", "fr"), "请更换头像")
	assert.equal(pickPhotoCopy("titleSet", "zh"), "请设置头像")
})

test("the day after the deadline follows the calendar", () => {
	assert.equal(nextDay("2026-10-06"), "2026-10-07")
	assert.equal(nextDay("2026-10-31"), "2026-11-01")
	assert.equal(nextDay("2026-12-31"), "2027-01-01")
	assert.equal(nextDay(null), "")
})

test("deadline is shown as month and day", () => {
	assert.equal(formatDeadline("2026-10-05", "zh"), "10月5日")
	assert.equal(formatDeadline("2026-10-05", "ja"), "10月5日")
	assert.equal(formatDeadline("2026-10-05", "en"), "Oct 5")
	assert.equal(formatDeadline(null, "zh"), "")
	assert.equal(formatDeadline("0001-01-01", "zh"), "")
})

test("a temporary photo gets the wording HR wrote, dates filled in", () => {
	assert.deepEqual(getReminderContent(temporary, "zh"), {
		title: "请更换头像",
		lead: ZH_CHANGE,
		overdue: false,
	})
	assert.equal(getReminderContent(temporary, "ja").lead, JA_CHANGE)
	assert.equal(getReminderContent({ ...temporary, overdue: true }, "zh").overdue, true)
	assert.equal(getReminderContent({ ...temporary, overdue: true }, "zh").lead, ZH_CHANGE)
})

test("a photo someone else set counts as temporary even without the flag", () => {
	const { temporary: _flag, ...older } = temporary
	assert.equal(getReminderContent(older, "zh").title, "请更换头像")
})

test("without any photo it asks to set one; without a deadline it drops the dates", () => {
	assert.equal(
		getReminderContent({ ...missing, deadline: "2026-10-06" }, "zh").lead,
		"因系统更新，自10月7日起，登录需使用您自行设置的头像。请最迟于10月6日完成设置。逾期将暂时无法登录。给您带来不便，敬请谅解。"
	)
	assert.equal(getReminderContent(missing, "zh").title, "请设置头像")
	for (const lang of ["zh", "ja", "en"]) {
		for (const status of [missing, { ...temporary, deadline: null }]) {
			assert.doesNotMatch(getReminderContent(status, lang).lead, /\{|月|Oct/)
		}
	}
})

test("wording does not ask for a photo of yourself", () => {
	for (const lang of ["zh", "ja", "en"]) {
		for (const text of [
			getReminderContent(temporary, lang).lead,
			getReminderContent(missing, lang).lead,
			getPromptCardContent(temporary, lang).message,
			getPromptCardContent(missing, lang).message,
			pickPhotoCopy("changeLead", lang),
		]) {
			assert.doesNotMatch(text, /本人|photo of yourself/, text)
		}
	}
})

test("home card asks to change a temporary photo or set a missing one", () => {
	assert.deepEqual(getPromptCardContent(temporary, "zh"), {
		title: "请更换头像",
		message: "当前头像为系统临时生成，请在10月6日前更换。",
		action: "去更换",
		overdue: false,
	})
	const overdue = getPromptCardContent({ ...temporary, overdue: true }, "zh")
	assert.equal(overdue.overdue, true)
	assert.equal(overdue.message, "当前头像为系统临时生成，已过更换期限（10月6日），请尽快更换。")
	assert.equal(
		getPromptCardContent({ ...temporary, deadline: null }, "zh").message,
		"当前头像为系统临时生成，请尽快更换。"
	)
	assert.deepEqual(getPromptCardContent(missing, "zh"), {
		title: "还没有设置头像",
		message: "请设置一张头像。",
		action: "去设置",
		overdue: false,
	})
	assert.equal(
		getPromptCardContent({ ...missing, deadline: "2026-10-06" }, "zh").message,
		"请在10月6日前设置。"
	)
})

test("home card stays short", () => {
	for (const status of [temporary, { ...temporary, overdue: true }, missing]) {
		assert.ok(getPromptCardContent(status, "zh").message.length <= 32)
	}
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
