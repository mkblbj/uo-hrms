import { normalizeLanguage } from "./language.js"

const DEFAULT_HOME_LANGUAGE = "zh"
export const CHECKIN_STATUS_CHANGED_EVENT = "checkin-status-changed"

const COPY = {
	zh: {
		statusWorking: "正在出勤",
		statusOff: "已退勤",
		statusPending: "待出勤",
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
		statusPending: "出勤前",
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
		statusPending: "Not Checked In",
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
		normalizeLanguage(boot?.lang) || normalizeLanguage(boot?.server_lang) || DEFAULT_HOME_LANGUAGE
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

export function emitCheckinStatusChanged(target = globalThis.window, detail = {}) {
	if (typeof target?.dispatchEvent !== "function") return false

	return target.dispatchEvent(createCheckinStatusChangedEvent(detail))
}

export function bindCheckinStatusRefresh(target = globalThis.window, reload = () => {}) {
	if (
		typeof target?.addEventListener !== "function" ||
		typeof target?.removeEventListener !== "function"
	) {
		return () => {}
	}

	const handleRefresh = (event) => reload(event)
	target.addEventListener(CHECKIN_STATUS_CHANGED_EVENT, handleRefresh)

	return () => target.removeEventListener(CHECKIN_STATUS_CHANGED_EVENT, handleRefresh)
}

function pick(lang, key) {
	return (
		COPY[normalizeLanguage(lang) || DEFAULT_HOME_LANGUAGE]?.[key] ||
		COPY[DEFAULT_HOME_LANGUAGE][key]
	)
}

function toDisplayTime(value) {
	if (!value) return "--:--"

	if (typeof value === "string") {
		const match = value.match(/(\d{2}):(\d{2})/)
		if (match) return `${match[1]}:${match[2]}`
	}

	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return "--:--"

	return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(
		2,
		"0"
	)}`
}

function withOverlayDescription(model, description) {
	Object.defineProperty(model, "description", {
		value: description,
		enumerable: false,
		configurable: true,
		writable: true,
	})

	return model
}

function resolveWorkStatusState(workStatus) {
	if (typeof workStatus === "string") {
		return ["working", "off_work", "no_checkin_today"].includes(workStatus) ? workStatus : null
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

export function getStatusChipMeta(workStatus, lang = "zh") {
	const resolvedWorkStatus = resolveWorkStatusState(workStatus)
	if (resolvedWorkStatus === null) return null

	const labelKeyByStatus = {
		working: "statusWorking",
		off_work: "statusOff",
		no_checkin_today: "statusPending",
	}

	const toneByStatus = {
		working: "working",
		off_work: "off",
		no_checkin_today: "pending",
	}

	return {
		label: pick(lang, labelKeyByStatus[resolvedWorkStatus]),
		tone: toneByStatus[resolvedWorkStatus],
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

export function getPrimaryScanAction(isWorking, translate = (value) => value) {
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

export function getPrimaryScanMeta(isWorking, lang = "zh", translate = (value) => value) {
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
		return (
			{
				zh: hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤",
				ja: hasCta ? "本日は出勤済みです。タップしてQRコードで退勤できます" : "本日は出勤済みです",
				en: hasCta
					? "You are checked in today. Tap to scan and check out."
					: "You are checked in today.",
			}[lang] || (hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤")
		)
	}

	if (status === "no_checkin_today") {
		return (
			{
				zh: hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录",
				ja: hasCta
					? "打刻履歴はまだありません。タップしてQRコードで出勤できます"
					: "打刻履歴はまだありません",
				en: hasCta
					? "No attendance record yet. Tap to scan and check in."
					: "No attendance record yet.",
			}[lang] || (hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录")
		)
	}

	const resolvedTimeText = workStatus?.last_checkin?.time
		? formatLastCheckin(workStatus.last_checkin.time)
		: timeText

	if (!resolvedTimeText) {
		return (
			{
				zh: hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录",
				ja: hasCta
					? "打刻履歴はまだありません。タップしてQRコードで出勤できます"
					: "打刻履歴はまだありません",
				en: hasCta
					? "No attendance record yet. Tap to scan and check in."
					: "No attendance record yet.",
			}[lang] || (hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录")
		)
	}

	return (
		{
			zh: hasCta ? `上次退勤 ${resolvedTimeText}，可点击扫码出勤` : `上次退勤 ${resolvedTimeText}`,
			ja: hasCta
				? `前回の退勤 ${resolvedTimeText}。タップしてQRコードで出勤できます`
				: `前回の退勤 ${resolvedTimeText}`,
			en: hasCta
				? `Last check-out ${resolvedTimeText}. Tap to scan and check in.`
				: `Last check-out ${resolvedTimeText}`,
		}[lang] ||
		(hasCta ? `上次退勤 ${resolvedTimeText}，可点击扫码出勤` : `上次退勤 ${resolvedTimeText}`)
	)
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

	const cta = allowPrimaryScan ? getPrimaryScanMeta(workStatus, lang, translate) : null

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

export function buildSuccessOverlayModel({
	action,
	lang = "zh",
	responseMessage,
	monthHours = 0,
}) {
	const resolvedLang = normalizeLanguage(lang) || DEFAULT_HOME_LANGUAGE

	if (action === "IN") {
		return withOverlayDescription(
			{
				variant: "checkin",
				statusLabel:
					{
						zh: "出勤成功",
						ja: "出勤成功",
						en: "Check-in Successful",
					}[resolvedLang] || "出勤成功",
				title:
					{
						zh: "开始上班",
						ja: "勤務開始",
						en: "Start Working",
					}[resolvedLang] || "开始上班",
				primaryLabel:
					{
						zh: "查看今日勤怠",
						ja: "今日の勤怠を見る",
						en: "View Today's Attendance",
					}[resolvedLang] || "查看今日勤怠",
				primaryRoute: { name: "AttendanceDashboard" },
				secondaryLabel:
					{
						zh: "关闭",
						ja: "閉じる",
						en: "Close",
					}[resolvedLang] || "关闭",
				delayMs: 1600,
				infoRows: [
					{
						label:
							{
								zh: "打卡时间",
								ja: "打刻時刻",
								en: "Time",
							}[resolvedLang] || "打卡时间",
						value: toDisplayTime(responseMessage?.time),
					},
					{
						label:
							{
								zh: "打卡方式",
								ja: "打刻方法",
								en: "Method",
							}[resolvedLang] || "打卡方式",
						value:
							{
								zh: "扫码 / PWA",
								ja: "QR / PWA",
								en: "QR / PWA",
							}[resolvedLang] || "扫码 / PWA",
					},
					{
						label:
							{
								zh: "地点",
								ja: "場所",
								en: "Location",
							}[resolvedLang] || "地点",
						value: responseMessage?.location || "--",
					},
				],
			},
			{
				zh: "你已完成今日出勤打卡。现在可以查看今日勤怠、班次与打卡记录。",
				ja: "本日の出勤打刻が完了しました。今日の勤怠、シフト、打刻履歴を確認できます。",
				en: "Today's check-in is complete. You can now review attendance, roster, and check-in records.",
			}[resolvedLang] || "你已完成今日出勤打卡。现在可以查看今日勤怠、班次与打卡记录。"
		)
	}

	return withOverlayDescription(
		{
			variant: "checkout",
			statusLabel:
				{
					zh: "退勤成功",
					ja: "退勤成功",
					en: "Check-out Successful",
				}[resolvedLang] || "退勤成功",
			title:
				{
					zh: "今天辛苦了",
					ja: "お疲れさまでした",
					en: "Great Work Today",
				}[resolvedLang] || "今天辛苦了",
			primaryLabel:
				{
					zh: "查看今日记录",
					ja: "今日の記録を見る",
					en: "View Today's Record",
				}[resolvedLang] || "查看今日记录",
			primaryRoute: { name: "EmployeeCheckinListView" },
			secondaryLabel:
				{
					zh: "关闭",
					ja: "閉じる",
					en: "Close",
				}[resolvedLang] || "关闭",
			delayMs: 1600,
			infoRows: [
				{
					label:
						{
							zh: "退勤时间",
							ja: "退勤時刻",
							en: "Check-out Time",
						}[resolvedLang] || "退勤时间",
					value: toDisplayTime(responseMessage?.time),
				},
				{
					label:
						{
							zh: "当月工时",
							ja: "今月の勤務時間",
							en: "This Month",
						}[resolvedLang] || "当月工时",
					value: `${Number(monthHours || 0).toFixed(2)} ${
						resolvedLang === "ja" ? "時間" : resolvedLang === "en" ? "hours" : "小时"
					}`,
				},
				{
					label:
						{
							zh: "说明",
							ja: "補足",
							en: "Note",
						}[resolvedLang] || "说明",
					value:
						{
							zh: "今天的工时信息，将于明天可查看。",
							ja: "本日の工時情報は明日確認できます。",
							en: "Today's hour details will be available tomorrow.",
						}[resolvedLang] || "今天的工时信息，将于明天可查看。",
				},
			],
		},
		{
			zh: "你已完成今日退勤打卡。系统已记录本次退勤时间，并显示当前当月工时。",
			ja: "本日の退勤打刻が完了しました。退勤時刻を記録し、今月の勤務時間を表示します。",
			en: "Today's check-out is complete. Your check-out time has been recorded and this month's hours are shown below.",
		}[resolvedLang] || "你已完成今日退勤打卡。系统已记录本次退勤时间，并显示当前当月工时。"
	)
}

export function getRosterEmptyCopy(lang = "zh") {
	return {
		today:
			{
				zh: "今日无班次",
				ja: "本日のシフトなし",
				en: "No shift today",
			}[lang] || "今日无班次",
		todayHint:
			{
				zh: "今天没有已发布排班",
				ja: "本日の公開済みシフトはありません",
				en: "No published shift today",
			}[lang] || "今天没有已发布排班",
		next:
			{
				zh: "暂无下个班次",
				ja: "次のシフトは未定です",
				en: "No next shift yet",
			}[lang] || "暂无下个班次",
		nextHint:
			{
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
