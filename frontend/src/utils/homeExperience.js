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
