const ATTENDANCE_COPY = {
	"legend.overtime": { zh: "加班", ja: "残業", en: "Overtime" },
	"legend.anomaly": { zh: "异常", ja: "異常", en: "Issue" },
	"legend.rest": { zh: "休", ja: "休", en: "Off" },
	"summary.title": { zh: "月度汇总", ja: "月次サマリー", en: "Monthly summary" },
	"summary.totalHours": { zh: "本月工时", ja: "今月時間", en: "Hours" },
	"summary.workDays": { zh: "出勤日", ja: "出勤日", en: "Days" },
	"summary.avgHours": { zh: "日均", ja: "平均", en: "Average" },
	"summary.progress": {
		zh: "已出勤 {done} / {total} 天",
		ja: "出勤 {done} / {total} 日",
		en: "{done} of {total} days",
	},
	"anomaly.notice": {
		zh: "本月有 {count} 天打卡异常",
		ja: "今月は{count}日打刻異常があります",
		en: "{count} days need attention this month",
	},
	"anomaly.action": { zh: "去修正", ja: "修正する", en: "Review" },
	"badge.rest": { zh: "休", ja: "休", en: "Off" },
	"badge.holiday": { zh: "节", ja: "祝", en: "Hol" },
	// A day that is clocked in but has no hours yet — typically today, still running.
	"badge.working": { zh: "出勤中", ja: "勤務中", en: "In" },
	"badge.checked_out": { zh: "已退勤", ja: "退勤済", en: "Out" },
	"badge.not_checked_in": { zh: "未打卡", ja: "未打刻", en: "No log" },
	"status.working": { zh: "出勤中", ja: "勤務中", en: "Working" },
	"status.checked_out": { zh: "已退勤", ja: "退勤済", en: "Checked out" },
	"status.not_checked_in": { zh: "未打卡", ja: "未打刻", en: "Not checked in" },
}

function normalizeLanguage(lang) {
	const base = String(lang || "zh").split("-")[0]
	return ["zh", "ja", "en"].includes(base) ? base : "zh"
}

export function getAttendanceCopy(key, lang, params = {}) {
	const language = normalizeLanguage(lang)
	const template = ATTENDANCE_COPY[key]?.[language] || ATTENDANCE_COPY[key]?.zh
	if (!template) return key
	return template.replace(/\{(\w+)\}/g, (match, name) =>
		Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match
	)
}
