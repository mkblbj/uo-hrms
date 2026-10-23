const ATTENDANCE_COPY = {
	"detail.totalHours": { zh: "总工时", ja: "合計勤務時間", en: "Total hours" },
	"detail.periods": { zh: "分段工时", ja: "勤務時間の内訳", en: "Work periods" },
	"detail.period": { zh: "第 {index} 段", ja: "第{index}区間", en: "Period {index}" },
	"detail.punches": { zh: "全部打卡记录", ja: "すべての打刻", en: "All punches" },
	"detail.checkIn": { zh: "签到", ja: "出勤", en: "Check-in" },
	"detail.checkOut": { zh: "签退", ja: "退勤", en: "Check-out" },
	"detail.punch": { zh: "打卡", ja: "打刻", en: "Punch" },
	"detail.countedTime": { zh: "计时时间", ja: "計算対象時間", en: "Counted time" },
	"detail.shortPeriod": {
		zh: "取整后不足一个计时单位",
		ja: "丸め後は集計単位に満たないため0時間",
		en: "No full time unit after rounding",
	},
	"detail.lunch": { zh: "午休扣除", ja: "昼休み控除", en: "Lunch deducted" },
	"detail.pending": { zh: "待结算", ja: "集計待ち", en: "Pending settlement" },
	"detail.completed": { zh: "已完成分段合计", ja: "完了区間の合計", en: "Completed periods" },
	"detail.openPeriod": { zh: "未签退", ja: "退勤未打刻", en: "Check-out pending" },
	"detail.noPeriods": {
		zh: "尚无完整的工作分段",
		ja: "完了した勤務区間はありません",
		en: "No complete work periods yet",
	},
	"detail.noPunches": {
		zh: "当天没有打卡记录",
		ja: "この日の打刻はありません",
		en: "No punches on this day",
	},
	"detail.correctionPunch": { zh: "补卡", ja: "打刻修正", en: "Correction" },
	"detail.excluded": { zh: "不计工时", ja: "集計対象外", en: "Not counted" },
	"detail.loading": {
		zh: "正在加载打卡明细…",
		ja: "打刻詳細を読み込み中…",
		en: "Loading punch details…",
	},
	"detail.loadError": {
		zh: "加载打卡明细失败",
		ja: "打刻詳細を読み込めませんでした",
		en: "Could not load punch details",
	},
	"detail.retry": { zh: "重试", ja: "再試行", en: "Retry" },
	"detail.totalDifference": {
		zh: "总工时与分段合计不同，请核对打卡记录。",
		ja: "確定時間と区間合計が異なります。打刻を確認してください。",
		en: "The settled total differs from the work periods. Review the punches.",
	},
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
