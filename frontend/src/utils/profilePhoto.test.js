import test from "node:test"
import assert from "node:assert/strict"
import * as photoUtils from "./profilePhoto.js"

import {
	PHOTO_MIN_SIDE,
	PHOTO_OUTPUT_SIZE,
	clampOffset,
	cropRect,
	getPromptCardContent,
	getReminderContent,
	maxZoomFor,
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
// HR 原话去掉日期和登录限制（2026-10-04 用户要求）
const ZH_CHANGE = "因系统更新，需使用您自行设置的头像。当前头像为系统临时生成，请尽快完成更换。给您带来不便，敬请谅解。"
const JA_CHANGE =
	"システム更新により、ご自身で設定したプロフィール画像が必要になります。現在の画像はシステムが仮に生成したものです。早めに変更をお願いいたします。ご不便をおかけしますが、ご理解のほどお願いいたします。"

test("copy is picked by language and falls back to Chinese", () => {
	assert.equal(pickPhotoCopy("titleChange", "zh"), "请更换头像")
	assert.equal(pickPhotoCopy("titleChange", "ja"), "プロフィール画像の変更")
	assert.equal(pickPhotoCopy("titleChange", "fr"), "请更换头像")
	assert.equal(pickPhotoCopy("titleSet", "zh"), "请设置头像")
})

test("a temporary photo gets HR's wording without dates or login limits", () => {
	assert.deepEqual(getReminderContent(temporary, "zh"), { title: "请更换头像", lead: ZH_CHANGE })
	assert.equal(getReminderContent(temporary, "ja").lead, JA_CHANGE)
	assert.deepEqual(getReminderContent({ ...temporary, overdue: true }, "zh"), {
		title: "请更换头像",
		lead: ZH_CHANGE,
	})
})

test("a photo someone else set counts as temporary even without the flag", () => {
	const { temporary: _flag, ...older } = temporary
	assert.equal(getReminderContent(older, "zh").title, "请更换头像")
})

test("without any photo it asks to set one", () => {
	assert.deepEqual(getReminderContent({ ...missing, deadline: "2026-10-06", overdue: true }, "zh"), {
		title: "请设置头像",
		lead: "因系统更新，需使用您自行设置的头像。请尽快完成设置。给您带来不便，敬请谅解。",
	})
})

test("the reminder and home card never mention a deadline or logging in", () => {
	const statuses = [
		temporary,
		{ ...temporary, overdue: true },
		{ ...missing, deadline: "2026-10-06" },
		{ ...missing, deadline: "2026-10-06", overdue: true },
	]
	for (const lang of ["zh", "ja", "en"]) {
		for (const status of statuses) {
			const reminder = getReminderContent(status, lang)
			const card = getPromptCardContent(status, lang)
			for (const text of [reminder.title, reminder.lead, card.title, card.message]) {
				assert.doesNotMatch(text, /登录|ログイン|log in|期限|截止|deadline|\{|10月|Oct/i, `${lang}: ${text}`)
			}
			assert.equal("deadline" in reminder, false)
			assert.equal(Boolean(card.overdue), false)
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
	for (const status of [temporary, { ...temporary, overdue: true }]) {
		assert.deepEqual(getPromptCardContent(status, "zh"), {
			title: "请更换头像",
			message: "当前头像为系统临时生成，请尽快更换。",
			action: "去更换",
		})
	}
	assert.deepEqual(getPromptCardContent({ ...missing, deadline: "2026-10-06" }, "zh"), {
		title: "还没有设置头像",
		message: "请设置一张头像。",
		action: "去设置",
	})
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

test("GIF preparation keeps the original bytes and the crop even when the MIME type is missing", async () => {
	for (const type of ["image/gif", ""]) {
		const file = new File(["GIF89a-original-animation"], "avatar.GIF", { type })
		const prepared = await photoUtils.preparePhotoUpload(file, {
			getCrop: () => ({ sx: 40, sy: 20, size: 200 }),
			exportBlob: () => {
				throw new Error("GIF must not be flattened by canvas")
			},
		})
		assert.equal(await prepared.blob.text(), "GIF89a-original-animation")
		assert.deepEqual(prepared.crop, { sx: 40, sy: 20, size: 200 })
	}
})

test("still photo preparation uses the cropped canvas image", async () => {
	const file = new File(["original"], "photo.png", { type: "image/png" })
	const prepared = await photoUtils.preparePhotoUpload(file, {
		exportBlob: async () => new Blob(["cropped-photo"], { type: "image/jpeg" }),
	})
	assert.equal(await prepared.blob.text(), "cropped-photo")
	assert.equal(prepared.blob.type, "image/jpeg")
	assert.equal(prepared.crop, null)
})

test("GIF upload sends a GIF filename, original bytes and crop coordinates", async () => {
	let body
	const fetchImpl = async (_url, options) => {
		body = options.body
		return { ok: true, status: 200, json: async () => ({ message: { photo: "/files/p.gif" } }) }
	}
	const photo = await uploadProfilePhoto(new Blob(["GIF89a-animation"], { type: "image/gif" }), {
		fetchImpl,
		crop: { sx: 40, sy: 20, size: 200 },
	})
	assert.equal(photo, "/files/p.gif")
	assert.equal(body.get("file").name, "profile-photo.gif")
	assert.equal(body.get("file").type, "image/gif")
	assert.equal(await body.get("file").text(), "GIF89a-animation")
	assert.deepEqual(JSON.parse(body.get("crop")), { sx: 40, sy: 20, size: 200 })
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
