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

function pick(lang, key) {
	return COPY[lang]?.[key] || COPY.zh[key]
}

export function resolveWorkStatusValue(workStatus) {
	if (typeof workStatus === "boolean") return workStatus

	const value = workStatus?.is_working
	return typeof value === "boolean" ? value : null
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
	isWorking,
	lang = "zh",
	timeText = "",
	hasCta = false,
}) {
	if (isWorking) {
		return {
			zh: hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤",
			ja: hasCta ? "本日は出勤済みです。タップしてQRコードで退勤できます" : "本日は出勤済みです",
			en: hasCta ? "You are checked in today. Tap to scan and check out." : "You are checked in today.",
		}[lang] || (hasCta ? "今天已出勤，可点击扫码退勤" : "今天已出勤")
	}

	if (!timeText) {
		return {
			zh: hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录",
			ja: hasCta ? "打刻履歴はまだありません。タップしてQRコードで出勤できます" : "打刻履歴はまだありません",
			en: hasCta ? "No attendance record yet. Tap to scan and check in." : "No attendance record yet.",
		}[lang] || (hasCta ? "暂无打卡记录，可点击扫码出勤" : "暂无打卡记录")
	}

	return {
		zh: hasCta ? `上次退勤 ${timeText}，可点击扫码出勤` : `上次退勤 ${timeText}`,
		ja: hasCta ? `前回の退勤 ${timeText}。タップしてQRコードで出勤できます` : `前回の退勤 ${timeText}`,
		en: hasCta ? `Last check-out ${timeText}. Tap to scan and check in.` : `Last check-out ${timeText}`,
	}[lang] || (hasCta ? `上次退勤 ${timeText}，可点击扫码出勤` : `上次退勤 ${timeText}`)
}

export function getHeroCardMeta({
	workStatus,
	lang = "zh",
	timeText = "",
	translate = (value) => value,
	allowPrimaryScan = true,
}) {
	const resolvedWorkStatus = resolveWorkStatusValue(workStatus)
	if (resolvedWorkStatus === null) {
		return {
			summary: null,
			cta: null,
		}
	}

	const cta = allowPrimaryScan
		? getPrimaryScanMeta(resolvedWorkStatus, lang, translate)
		: null

	return {
		summary: getHeroSummaryCopy({
			isWorking: resolvedWorkStatus,
			lang,
			timeText,
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
