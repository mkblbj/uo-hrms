export const ATTENDANCE_ANOMALY_COLOR = "#dc2626"

const COPY = {
	zh: {
		anomaly: "异常",
		missing_checkout: "缺少签退",
		missing_checkin: "缺少签到",
		invalid_sequence: "打卡顺序异常",
	},
	ja: {
		anomaly: "異常",
		missing_checkout: "退勤打刻がありません",
		missing_checkin: "出勤打刻がありません",
		invalid_sequence: "打刻順序の異常",
	},
	en: {
		anomaly: "Issue",
		missing_checkout: "Missing check-out",
		missing_checkin: "Missing check-in",
		invalid_sequence: "Invalid check-in sequence",
	},
}

function normalizeLang(lang) {
	const value = String(lang || "zh").replace("_", "-").toLowerCase()
	return value.split("-", 1)[0]
}

function copyFor(lang) {
	return COPY[normalizeLang(lang)] || COPY.zh
}

export function hasAttendanceAnomaly(anomaly) {
	return Boolean(anomaly?.has_issue)
}

export function getAttendanceAnomalyTitle(lang = "zh") {
	return copyFor(lang).anomaly
}

export function getAttendanceAnomalyLabel(anomaly, lang = "zh") {
	if (!hasAttendanceAnomaly(anomaly)) return ""
	const dict = copyFor(lang)
	const code = anomaly?.codes?.[0]
	return dict[code] || anomaly?.label || dict.anomaly
}
