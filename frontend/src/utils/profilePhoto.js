// 头像：提醒节奏、圆形取景框的裁剪计算、上传，以及界面文案。

import { extractFrappeError } from "./passkeyCheckin.js"

export const PHOTO_OUTPUT_SIZE = 512
export const PHOTO_MIN_SIDE = 128
export const PHOTO_MAX_ZOOM = 4
export const PHOTO_REMINDER_SNOOZE_MS = 3 * 60 * 60 * 1000
export const PHOTO_REMINDER_STORAGE_KEY = "hrms:profile-photo-snoozed-at"
export const PHOTO_STATUS_METHOD = "hrms.api.profile_photo.get_profile_photo_status"
export const PHOTO_UPLOAD_METHOD = "hrms.api.profile_photo.upload_my_photo"

const COPY = {
	title: {
		zh: "请设置头像",
		ja: "プロフィール写真の設定",
		en: "Please Set a Profile Photo",
	},
	deadline: { zh: "请在 {0} 前完成", ja: "{0}までに設定してください", en: "Please finish by {0}" },
	overdue: {
		zh: "已过截止日期（{0}），请尽快设置",
		ja: "期限（{0}）を過ぎています。早めに設定してください",
		en: "The deadline ({0}) has passed. Please set it soon",
	},
	lead: {
		zh: "系统更新，需要每个人设置一张头像（请用本人照片），1 分钟就好。",
		ja: "システム更新のため、ご本人の写真を設定してください。1分ほどで終わります。",
		en: "After a system update, everyone needs a profile photo (a photo of yourself). It only takes a minute.",
	},
	takePhoto: { zh: "拍一张", ja: "写真を撮る", en: "Take a Photo" },
	choosePhoto: { zh: "从相册选择", ja: "アルバムから選ぶ", en: "Choose from Library" },
	later: { zh: "稍后再说", ja: "あとで", en: "Later" },
	cancel: { zh: "取消", ja: "キャンセル", en: "Cancel" },
	changeTitle: { zh: "更换头像", ja: "写真を変更", en: "Change Photo" },
	changeLead: {
		zh: "请选一张本人照片。",
		ja: "ご本人の写真を選んでください。",
		en: "Choose a photo of yourself.",
	},
	editTitle: { zh: "调整头像", ja: "写真の調整", en: "Adjust Your Photo" },
	editHint: {
		zh: "拖动照片调整位置，双指或拖动滑块缩放",
		ja: "ドラッグで位置を、ピンチかスライダーで大きさを調整できます",
		en: "Drag to move. Pinch or use the slider to zoom.",
	},
	zoom: { zh: "缩放", ja: "拡大・縮小", en: "Zoom" },
	usePhoto: { zh: "使用这张", ja: "この写真を使う", en: "Use This Photo" },
	chooseAgain: { zh: "重新选择", ja: "選び直す", en: "Choose Another" },
	uploading: { zh: "正在上传…", ja: "アップロード中…", en: "Uploading…" },
	uploaded: {
		zh: "头像已更新",
		ja: "プロフィール写真を更新しました",
		en: "Profile photo updated",
	},
	readFailed: {
		zh: "无法读取这张照片，请换一张。",
		ja: "この写真を読み込めませんでした。別の写真を選んでください。",
		en: "This photo could not be opened. Please choose another one.",
	},
	tooSmall: {
		zh: "照片太小了，请换一张更清晰的。",
		ja: "写真が小さすぎます。もっと鮮明な写真を選んでください。",
		en: "This photo is too small. Please choose a clearer one.",
	},
	uploadFailed: {
		zh: "上传失败，请重试。",
		ja: "アップロードに失敗しました。もう一度お試しください。",
		en: "Upload failed. Please try again.",
	},
	cardTitle: {
		zh: "还没有设置头像",
		ja: "プロフィール写真が未設定です",
		en: "No Profile Photo Yet",
	},
	cardDeadline: {
		zh: "请在 {0} 前设置。",
		ja: "{0}までに設定してください。",
		en: "Please set it by {0}.",
	},
	cardOverdue: {
		zh: "已过截止日期（{0}），请尽快设置。",
		ja: "期限（{0}）を過ぎています。早めに設定してください。",
		en: "The deadline ({0}) has passed. Please set it soon.",
	},
	cardNoDeadline: {
		zh: "系统更新，需要设置一张头像。",
		ja: "システム更新のため、プロフィール写真を設定してください。",
		en: "After a system update, please set a profile photo.",
	},
	cardAction: { zh: "去设置", ja: "設定する", en: "Set Photo" },
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

export function pickPhotoCopy(key, lang = "zh", ...args) {
	const entry = COPY[key] || {}
	const text = entry[lang] || entry.zh || ""
	return args.reduce((result, value, index) => result.replace(`{${index}}`, value), text)
}

export function formatDeadline(value, lang = "zh") {
	const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ""))
	if (!match || Number(match[1]) < 2000) return ""
	const month = Number(match[2])
	const day = Number(match[3])
	return lang === "en" ? `${MONTHS[month - 1]} ${day}` : `${month}月${day}日`
}

export function shouldShowPhotoReminder(status, { now = Date.now(), snoozedAt = null } = {}) {
	if (!status?.required || status?.has_photo) return false
	const snoozedRecently =
		snoozedAt && now >= snoozedAt && now - snoozedAt < PHOTO_REMINDER_SNOOZE_MS
	return !snoozedRecently
}

export function readSnoozedAt(storage = globalThis.localStorage) {
	try {
		const value = Number(storage?.getItem(PHOTO_REMINDER_STORAGE_KEY))
		return Number.isFinite(value) && value > 0 ? value : null
	} catch (_) {
		return null
	}
}

export function writeSnoozedAt(storage = globalThis.localStorage, now = Date.now()) {
	try {
		storage?.setItem(PHOTO_REMINDER_STORAGE_KEY, String(now))
	} catch (_) {
		// 存不了就每次打开都提醒
	}
}

function deadlineText(status, lang, key, overdueKey) {
	const deadline = formatDeadline(status?.deadline, lang)
	if (!deadline) return { text: "", overdue: false }
	const overdue = Boolean(status?.overdue)
	return { text: pickPhotoCopy(overdue ? overdueKey : key, lang, deadline), overdue }
}

export function getReminderContent(status, lang = "zh") {
	const deadline = deadlineText(status, lang, "deadline", "overdue")
	return {
		title: pickPhotoCopy("title", lang),
		deadline: deadline.text,
		overdue: deadline.overdue,
		lead: pickPhotoCopy("lead", lang),
	}
}

export function getPromptCardContent(status, lang = "zh") {
	const deadline = deadlineText(status, lang, "cardDeadline", "cardOverdue")
	return {
		title: pickPhotoCopy("cardTitle", lang),
		message: deadline.text || pickPhotoCopy("cardNoDeadline", lang),
		action: pickPhotoCopy("cardAction", lang),
		overdue: deadline.overdue,
	}
}

function clamp(value, min, max) {
	return Math.min(Math.max(value, min), max) || 0
}

// 取景框是边长 viewport 的正方形（圆形遮罩），照片按 cover 铺满后再乘 zoom；
// x、y 是照片中心相对取景框中心的偏移（屏幕像素）。
function imageScale({ width, height, viewport, zoom }) {
	return (viewport / Math.min(width, height)) * zoom
}

export function clampOffset({ width, height, viewport, zoom, x, y }) {
	const scale = imageScale({ width, height, viewport, zoom })
	const maxX = Math.max(0, (width * scale - viewport) / 2)
	const maxY = Math.max(0, (height * scale - viewport) / 2)
	return { x: clamp(x, -maxX, maxX), y: clamp(y, -maxY, maxY) }
}

export function cropRect({ width, height, viewport, zoom, x, y }) {
	const size = Math.min(width, height) / zoom
	const imagePerScreen = size / viewport
	const sx = width / 2 - x * imagePerScreen - size / 2
	const sy = height / 2 - y * imagePerScreen - size / 2
	return { sx: clamp(sx, 0, width - size), sy: clamp(sy, 0, height - size), size }
}

export function maxZoomFor(width, height) {
	return Math.max(1, Math.min(PHOTO_MAX_ZOOM, Math.min(width, height) / PHOTO_MIN_SIDE))
}

export function outputSizeFor(cropSize) {
	return Math.max(PHOTO_MIN_SIDE, Math.min(PHOTO_OUTPUT_SIZE, Math.round(cropSize)))
}

export async function uploadProfilePhoto(
	blob,
	{
		fetchImpl = globalThis.fetch?.bind(globalThis),
		csrfToken = globalThis.window?.csrf_token,
	} = {}
) {
	const body = new FormData()
	body.append("file", blob, "profile-photo.jpg")
	const response = await fetchImpl(`/api/method/${PHOTO_UPLOAD_METHOD}`, {
		method: "POST",
		headers: { Accept: "application/json", "X-Frappe-CSRF-Token": csrfToken || "" },
		body,
		credentials: "same-origin",
	})
	let data = {}
	try {
		data = await response.json()
	} catch (_) {
		data = {}
	}
	const photo = data?.message?.photo
	if (!response.ok || !photo) {
		const error = new Error(extractFrappeError(data))
		error.status = response.status
		throw error
	}
	return photo
}
