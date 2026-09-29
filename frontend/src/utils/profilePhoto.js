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
		zh: "请上传本人头像",
		ja: "プロフィール写真を登録してください",
		en: "Please Add Your Profile Photo",
	},
	deadline: { zh: "请在 {0} 前完成", ja: "{0}までに登録してください", en: "Please finish by {0}" },
	overdue: {
		zh: "已超过截止日期（{0}），请尽快上传",
		ja: "登録期限（{0}）を過ぎています。至急登録してください",
		en: "The deadline ({0}) has passed. Please add it now",
	},
	lead: {
		zh: "公司请每位员工上传一张本人照片作为头像，1 分钟就能完成。",
		ja: "全従業員に、本人の写真をプロフィール写真として登録していただいています。1分ほどで終わります。",
		en: "Everyone is asked to add a photo of themselves as their profile photo. It takes about a minute.",
	},
	usesTitle: { zh: "用在哪里", ja: "利用目的", en: "Where It Is Used" },
	useCheckin: {
		zh: "打卡确认：门口打卡屏会显示打卡人的头像，方便确认是本人打卡。",
		ja: "打刻の確認：入口の打刻画面に打刻した人の写真が表示され、本人の打刻か確認できます。",
		en: "Check-in: the screen at the door shows the photo of whoever checks in, so it is clear the right person did.",
	},
	useRequests: {
		zh: "申请与通知：请假、补卡等申请和系统通知会显示头像，一眼认出是谁。",
		ja: "申請・通知：休暇や打刻修正などの申請、お知らせに写真が表示され、誰からか一目で分かります。",
		en: "Requests and notifications: leave and correction requests and notifications show your photo, so people know who it is at a glance.",
	},
	useFuture: {
		zh: "以后的新功能：公司内部系统以后新增的功能也用这张头像，这次统一收集，以后不用重复提交。",
		ja: "今後の新機能：社内システムに今後追加する機能でも同じ写真を使います。今回まとめて登録すれば、改めて提出する必要はありません。",
		en: "Future features: new features in our internal systems will use the same photo, so you only need to add it once.",
	},
	rulesTitle: { zh: "照片要求", ja: "写真の条件", en: "Photo Guidelines" },
	ruleFace: {
		zh: "本人近照，正面，五官清晰，不戴口罩和墨镜。",
		ja: "本人の最近の写真で、正面から顔がはっきり写っているもの（マスク・サングラスなし）。",
		en: "A recent photo of you, facing the camera with your face clearly visible, no mask or sunglasses.",
	},
	ruleNot: {
		zh: "不用风景、卡通、合影或别人的照片。",
		ja: "風景・イラスト・集合写真・他人の写真は使えません。",
		en: "No scenery, cartoons, group photos or photos of other people.",
	},
	promiseTitle: { zh: "我们承诺", ja: "お約束", en: "Our Promise" },
	promiseInternal: {
		zh: "只在公司内部系统里显示，不对外公开，不提供给第三方。",
		ja: "社内システムの中だけで表示し、社外への公開や第三者への提供はしません。",
		en: "Shown only inside our internal systems, never published or shared with third parties.",
	},
	promiseNoFaceId: {
		zh: "不用于人脸识别。面容/指纹打卡由你的手机自己验证，面部和指纹数据只在手机里，公司拿不到。",
		ja: "顔認証には使いません。顔・指紋での打刻はスマートフォン自身が確認しており、顔や指紋のデータはスマートフォンの中にだけあり、会社には届きません。",
		en: "Never used for face recognition. Face ID and fingerprint check-in is verified by your phone; that data stays on your phone and never reaches the company.",
	},
	promiseDelete: {
		zh: "离职后删除。",
		ja: "退職後は削除します。",
		en: "Deleted when you leave the company.",
	},
	takePhoto: { zh: "拍一张", ja: "写真を撮る", en: "Take a Photo" },
	choosePhoto: { zh: "从相册选择", ja: "アルバムから選ぶ", en: "Choose from Library" },
	later: { zh: "稍后再说", ja: "あとで", en: "Later" },
	cancel: { zh: "取消", ja: "キャンセル", en: "Cancel" },
	changeTitle: { zh: "更换头像", ja: "写真を変更", en: "Change Photo" },
	changeLead: {
		zh: "请选择一张本人近照，正面、五官清晰。",
		ja: "本人の最近の写真で、顔がはっきり写っているものを選んでください。",
		en: "Choose a recent photo of you with your face clearly visible.",
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
		zh: "还没有上传头像",
		ja: "プロフィール写真が未登録です",
		en: "No Profile Photo Yet",
	},
	cardDeadline: {
		zh: "请在 {0} 前上传本人照片。",
		ja: "{0}までに本人の写真を登録してください。",
		en: "Please add a photo of yourself by {0}.",
	},
	cardOverdue: {
		zh: "已超过截止日期（{0}），请尽快上传。",
		ja: "登録期限（{0}）を過ぎています。至急登録してください。",
		en: "The deadline ({0}) has passed. Please add it now.",
	},
	cardNoDeadline: {
		zh: "请上传一张本人照片作为头像。",
		ja: "本人の写真をプロフィール写真として登録してください。",
		en: "Please add a photo of yourself as your profile photo.",
	},
	cardAction: { zh: "去上传", ja: "登録する", en: "Add Photo" },
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
	const t = (key) => pickPhotoCopy(key, lang)
	const deadline = deadlineText(status, lang, "deadline", "overdue")
	return {
		title: t("title"),
		deadline: deadline.text,
		overdue: deadline.overdue,
		lead: t("lead"),
		sections: [
			{
				id: "uses",
				title: t("usesTitle"),
				items: [t("useCheckin"), t("useRequests"), t("useFuture")],
			},
			{ id: "rules", title: t("rulesTitle"), items: [t("ruleFace"), t("ruleNot")] },
			{
				id: "promise",
				title: t("promiseTitle"),
				items: [t("promiseInternal"), t("promiseNoFaceId"), t("promiseDelete")],
			},
		],
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
