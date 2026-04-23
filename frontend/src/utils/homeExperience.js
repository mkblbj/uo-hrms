import { normalizeLanguage } from "./language.js"

const DEFAULT_HOME_LANGUAGE = "zh"
export const CHECKIN_STATUS_CHANGED_EVENT = "checkin-status-changed"

const COPY = {
	zh: {
		statusWorking: "正在出勤",
		statusOff: "已退勤",
		scanInTitle: "扫码出勤",
		scanInDescription: "打开相机进行打卡",
		scanOutTitle: "扫码退勤",
		scanOutDescription: "打开相机完成退勤",
		settingsLanguageTitle: "应用语言",
		settingsLanguageDescription: "选择首页和成功反馈使用的语言",
		tabHome: "首页",
		tabAttendance: "勤怠",
		tabRoster: "排班",
		tabExpenses: "经费",
		tabSalary: "工资",
	},
	ja: {
		statusWorking: "勤務中",
		statusOff: "退勤済",
		scanInTitle: "QRコードで出勤",
		scanInDescription: "カメラを起動して打刻します",
		scanOutTitle: "QRコードで退勤",
		scanOutDescription: "カメラを起動して退勤します",
		settingsLanguageTitle: "アプリ言語",
		settingsLanguageDescription: "ホーム画面と成功演出に使う言語を選択します",
		tabHome: "ホーム",
		tabAttendance: "勤怠",
		tabRoster: "シフト",
		tabExpenses: "経費",
		tabSalary: "給与",
	},
	en: {
		statusWorking: "Working",
		statusOff: "Off Work",
		scanInTitle: "Scan to Check In",
		scanInDescription: "Open the camera to record attendance",
		scanOutTitle: "Scan to Check Out",
		scanOutDescription: "Open the camera to finish check-out",
		settingsLanguageTitle: "App Language",
		settingsLanguageDescription:
			"Choose the language used across the home screen and success feedback",
		tabHome: "Home",
		tabAttendance: "Attendance",
		tabRoster: "Roster",
		tabExpenses: "Expenses",
		tabSalary: "Salary",
	},
}

export function resolveHomeLanguage(boot = globalThis.window?.frappe?.boot) {
	return (
		normalizeLanguage(boot?.lang) ||
		normalizeLanguage(boot?.server_lang) ||
		DEFAULT_HOME_LANGUAGE
	)
}

function createCheckinStatusChangedEvent(detail = {}) {
	if (typeof globalThis.CustomEvent === "function") {
		return new CustomEvent(CHECKIN_STATUS_CHANGED_EVENT, { detail })
	}

	const event = new Event(CHECKIN_STATUS_CHANGED_EVENT)
	Object.defineProperty(event, "detail", {
		value: detail,
		enumerable: true,
	})
	return event
}

export function emitCheckinStatusChanged(
	target = globalThis.window,
	detail = {},
) {
	if (typeof target?.dispatchEvent !== "function") return false

	return target.dispatchEvent(createCheckinStatusChangedEvent(detail))
}

export function bindCheckinStatusRefresh(
	target = globalThis.window,
	reload = () => {},
) {
	if (
		typeof target?.addEventListener !== "function"
		|| typeof target?.removeEventListener !== "function"
	) {
		return () => {}
	}

	const handleRefresh = (event) => reload(event)
	target.addEventListener(CHECKIN_STATUS_CHANGED_EVENT, handleRefresh)

	return () => target.removeEventListener(CHECKIN_STATUS_CHANGED_EVENT, handleRefresh)
}

function pick(lang, key) {
	return COPY[normalizeLanguage(lang) || DEFAULT_HOME_LANGUAGE]?.[key] || COPY[DEFAULT_HOME_LANGUAGE][key]
}

function resolveWorkStatusState(workStatus) {
	if (typeof workStatus === "string") {
		return ["working", "off_work", "no_checkin_today"].includes(workStatus)
			? workStatus
			: null
	}

	const status = workStatus?.status
	if (["working", "off_work", "no_checkin_today"].includes(status)) {
		return status
	}

	if (typeof workStatus === "boolean") {
		return workStatus ? "working" : "off_work"
	}

	const value = workStatus?.is_working
	return typeof value === "boolean" ? (value ? "working" : "off_work") : null
}

export function resolveWorkStatusValue(workStatus) {
	const status = resolveWorkStatusState(workStatus)
	if (status === null) return null

	return status === "working"
}

export function getStatusChipMeta(isWorking, lang = "zh") {
	const resolvedWorkStatus = resolveWorkStatusValue(isWorking)
	if (resolvedWorkStatus === null) return null

	return {
		label: pick(lang, resolvedWorkStatus ? "statusWorking" : "statusOff"),
		tone: resolvedWorkStatus ? "working" : "off",
		routeName: "AttendanceDashboard",
	}
}

export function getPrimaryScanCopy(isWorking, lang = "zh") {
	const resolvedWorkStatus = resolveWorkStatusValue(isWorking)
	if (resolvedWorkStatus === null) return null

	return resolvedWorkStatus
		? {
				title: pick(lang, "scanOutTitle"),
				description: pick(lang, "scanOutDescription"),
			}
		: {
				title: pick(lang, "scanInTitle"),
				description: pick(lang, "scanInDescription"),
			}
}

export function getPrimaryScanAction(
	isWorking,
	translate = (value) => value,
) {
	const resolvedWorkStatus = resolveWorkStatusValue(isWorking)
	if (resolvedWorkStatus === null) return null

	return resolvedWorkStatus
		? {
				action: "OUT",
				label: translate("Check Out"),
			}
		: {
				action: "IN",
				label: translate("Check In"),
			}
}

export function getPrimaryScanMeta(
	isWorking,
	lang = "zh",
	translate = (value) => value,
) {
	const action = getPrimaryScanAction(isWorking, translate)
	const copy = getPrimaryScanCopy(isWorking, lang)

	return action && copy ? { ...action, ...copy } : null
}

export function getHeroSummaryCopy({
	workStatus,
	isWorking,
	lang = "zh",
	timeText = "",
	formatLastCheckin = (value) => value,
	hasCta = false,
}) {
	const status = resolveWorkStatusState(workStatus ?? isWorking)
	if (status === null) return null

	if (status === "working") {
		return {
			zh: hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤",
			ja: hasCta ? "本日は出勤済みです。タップしてQRコードで退勤できます" : "本日は出勤済みです",
			en: hasCta ? "You are checked in today. Tap to scan and check out." : "You are checked in today.",
		}[lang] || (hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤")
	}

	if (status === "no_checkin_today") {
		return {
			zh: hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录",
			ja: hasCta ? "打刻履歴はまだありません。タップしてQRコードで出勤できます" : "打刻履歴はまだありません",
			en: hasCta ? "No attendance record yet. Tap to scan and check in." : "No attendance record yet.",
		}[lang] || (hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录")
	}

	const resolvedTimeText = workStatus?.last_checkin?.time
		? formatLastCheckin(workStatus.last_checkin.time)
		: timeText

	if (!resolvedTimeText) {
		return {
			zh: hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录",
			ja: hasCta ? "打刻履歴はまだありません。タップしてQRコードで出勤できます" : "打刻履歴はまだありません",
			en: hasCta ? "No attendance record yet. Tap to scan and check in." : "No attendance record yet.",
		}[lang] || (hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录")
	}

	return {
		zh: hasCta
			? `上次退勤 ${resolvedTimeText}，可点击扫码出勤`
			: `上次退勤 ${resolvedTimeText}`,
		ja: hasCta
			? `前回の退勤 ${resolvedTimeText}。タップしてQRコードで出勤できます`
			: `前回の退勤 ${resolvedTimeText}`,
		en: hasCta
			? `Last check-out ${resolvedTimeText}. Tap to scan and check in.`
			: `Last check-out ${resolvedTimeText}`,
	}[lang]
		|| (hasCta
			? `上次退勤 ${resolvedTimeText}，可点击扫码出勤`
			: `上次退勤 ${resolvedTimeText}`)
}

export function getHeroCardMeta({
	workStatus,
	lang = "zh",
	timeText = "",
	formatLastCheckin = (value) => value,
	translate = (value) => value,
	allowPrimaryScan = true,
}) {
	if (resolveWorkStatusState(workStatus) === null) {
		return {
			summary: null,
			cta: null,
		}
	}

	const cta = allowPrimaryScan
		? getPrimaryScanMeta(workStatus, lang, translate)
		: null

	return {
		summary: getHeroSummaryCopy({
			workStatus,
			lang,
			timeText,
			formatLastCheckin,
			hasCta: Boolean(cta),
		}),
		cta,
	}
}

export function getRosterEmptyCopy(lang = "zh") {
	return {
		today: {
			zh: "今日无班次",
			ja: "本日のシフトなし",
			en: "No shift today",
		}[lang] || "今日无班次",
		todayHint: {
			zh: "今天没有已发布排班",
			ja: "本日の公開済みシフトはありません",
			en: "No published shift today",
		}[lang] || "今天没有已发布排班",
		next: {
			zh: "暂无下个班次",
			ja: "次のシフトは未定です",
			en: "No next shift yet",
		}[lang] || "暂无下个班次",
		nextHint: {
			zh: "后续班次尚未发布",
			ja: "後続シフトはまだ公開されていません",
			en: "Upcoming shifts are not published yet",
		}[lang] || "后续班次尚未发布",
	}
}

export function getBottomTabItems(lang = "zh") {
	return [
		{ key: "home", title: pick(lang, "tabHome"), route: "/home" },
		{ key: "attendance", title: pick(lang, "tabAttendance"), route: "/dashboard/attendance" },
		{ key: "roster", title: pick(lang, "tabRoster"), route: "/dashboard/work-roster" },
		{ key: "expenses", title: pick(lang, "tabExpenses"), route: "/dashboard/expense-claims" },
		{ key: "salary", title: pick(lang, "tabSalary"), route: "/dashboard/salary-slips" },
	]
}

export function getLanguageCardCopy(lang = "zh") {
	return {
		title: pick(lang, "settingsLanguageTitle"),
		description: pick(lang, "settingsLanguageDescription"),
	}
}
