const LABELS = {
	zh: {
		pending: "待出勤",
		working: "出勤中",
		overtime: "加班中",
		done: "已退勤",
	},
	ja: {
		pending: "出勤前",
		working: "勤務中",
		overtime: "残業中",
		done: "退勤済",
	},
	en: {
		pending: "Pending",
		working: "Working",
		overtime: "Overtime",
		done: "Off Work",
	},
}

const OVERTIME_COPY = {
	zh: {
		activePrefix: "已超",
		donePrefix: "加班",
		totalPrefix: "共",
	},
	ja: {
		activePrefix: "超過",
		donePrefix: "残業",
		totalPrefix: "合計",
	},
	en: {
		activePrefix: "Over by",
		donePrefix: "Overtime",
		totalPrefix: "Total",
	},
}

function pickLabel(lang, key) {
	return LABELS[lang]?.[key] || LABELS.zh[key]
}

function pickOvertimeCopy(lang) {
	return OVERTIME_COPY[lang] || OVERTIME_COPY.zh
}

function normalizeTimeText(value) {
	if (!value) return ""
	const text = String(value).trim()
	const match = text.match(/(\d{1,2}):(\d{2})/)
	if (!match) return ""
	return `${match[1].padStart(2, "0")}:${match[2]}`
}

function normalizeDateText(value) {
	if (!value) return ""
	if (value instanceof Date) {
		return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(
			value.getDate()
		).padStart(2, "0")}`
	}
	return String(value).slice(0, 10)
}

function parseDateTime(value) {
	if (!value) return null
	if (value instanceof Date) {
		const copy = new Date(value)
		return Number.isNaN(copy.getTime()) ? null : copy
	}

	const normalized = String(value).trim().replace(" ", "T")
	const date = new Date(normalized)
	return Number.isNaN(date.getTime()) ? null : date
}

function parseScheduleTime(schedule, key) {
	const directValue = normalizeTimeText(schedule?.[key])
	if (directValue) return directValue

	const scheduledTime = String(schedule?.scheduled_time || "")
	const parts = scheduledTime.split("-")
	return normalizeTimeText(key === "start_time" ? parts[0] : parts[1])
}

function buildScheduleDateTime(dateText, timeText) {
	if (!dateText || !timeText) return null
	const date = new Date(`${dateText}T${timeText}:00`)
	return Number.isNaN(date.getTime()) ? null : date
}

function addDays(date, days) {
	const next = new Date(date)
	next.setDate(next.getDate() + days)
	return next
}

function diffHours(end, start) {
	return Math.max(0, (end.getTime() - start.getTime()) / 36e5)
}

function clamp(value, min, max) {
	return Math.min(Math.max(value, min), max)
}

function roundPercent(value) {
	return Math.round(value * 100) / 100
}

function roundHours(value) {
	return Math.round(value * 100) / 100
}

function resolveStatus(workStatus) {
	if (workStatus?.status) return workStatus.status
	if (typeof workStatus === "boolean") return workStatus ? "working" : "off_work"
	if (typeof workStatus?.is_working === "boolean")
		return workStatus.is_working ? "working" : "off_work"
	return "no_checkin_today"
}

function resolveStartTime({ stats, workStatus }) {
	return (
		parseDateTime(stats?.first_checkin_today) ||
		(workStatus?.last_checkin?.log_type === "IN"
			? parseDateTime(workStatus.last_checkin.time)
			: null)
	)
}

function resolveEndTime({ stats, workStatus, now, status }) {
	if (status === "working") return now
	return (
		parseDateTime(stats?.last_checkin_today) ||
		(workStatus?.last_checkin?.log_type === "OUT"
			? parseDateTime(workStatus.last_checkin.time)
			: null)
	)
}

function buildWorkedLabel({
	hasOvertime,
	statusKey,
	overtimeHours,
	totalWorkedHours,
	workedHours,
	shiftHours,
	lang,
}) {
	if (!hasOvertime) {
		return `${workedHours.toFixed(1)} / ${shiftHours.toFixed(1)}h`
	}

	const copy = pickOvertimeCopy(lang)
	const prefix = statusKey === "overtime" ? copy.activePrefix : copy.donePrefix
	return `${prefix} ${overtimeHours.toFixed(1)}h · ${copy.totalPrefix} ${totalWorkedHours.toFixed(
		1
	)}h`
}

export function buildShiftProgress({
	schedule,
	stats = {},
	workStatus = null,
	now = new Date(),
	lang = "zh",
} = {}) {
	const dateText = normalizeDateText(schedule?.date)
	const startText = parseScheduleTime(schedule, "start_time")
	const endText = parseScheduleTime(schedule, "end_time")
	const scheduledStart = buildScheduleDateTime(dateText, startText)
	let scheduledEnd = buildScheduleDateTime(dateText, endText)
	if (!scheduledStart || !scheduledEnd) return null

	if (scheduledEnd <= scheduledStart) {
		scheduledEnd = addDays(scheduledEnd, 1)
	}

	const nowValue = parseDateTime(now) || new Date()
	const shiftHours = diffHours(scheduledEnd, scheduledStart)
	if (shiftHours <= 0) return null

	const status = resolveStatus(workStatus)
	const actualStart = resolveStartTime({ stats, workStatus })
	const actualEnd = resolveEndTime({ stats, workStatus, now: nowValue, status })
	let workedHours = 0
	let totalWorkedHours = 0

	if (actualStart && actualEnd && actualEnd > actualStart) {
		const boundedStart = actualStart < scheduledStart ? scheduledStart : actualStart
		const boundedEnd = actualEnd > scheduledEnd ? scheduledEnd : actualEnd
		workedHours = diffHours(boundedEnd, boundedStart)
		totalWorkedHours = diffHours(actualEnd, boundedStart)
	}

	const overtimeHours = roundHours(Math.max(0, totalWorkedHours - workedHours))
	const hasOvertime = overtimeHours > 0
	const statusKey =
		status === "working" && hasOvertime
			? "overtime"
			: status === "working"
			? "working"
			: status === "off_work"
			? "done"
			: "pending"
	const percent = hasOvertime ? 100 : roundPercent(clamp((workedHours / shiftHours) * 100, 0, 100))

	return {
		percent,
		statusKey,
		statusLabel: pickLabel(lang, statusKey),
		rangeLabel: schedule?.scheduled_time || `${startText}-${endText}`,
		workedLabel: buildWorkedLabel({
			hasOvertime,
			statusKey,
			overtimeHours,
			totalWorkedHours,
			workedHours,
			shiftHours,
			lang,
		}),
		shiftHours,
		workedHours: roundHours(workedHours),
		totalWorkedHours: roundHours(totalWorkedHours),
		overtimeHours,
		hasOvertime,
		tone: hasOvertime ? "overtime" : "normal",
	}
}
