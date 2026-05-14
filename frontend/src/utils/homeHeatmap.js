export const DEFAULT_STANDARD_DAY_HOURS = 8

const NO_ATTENDANCE_COLOR = "#fde68a"
const LEVEL_COLORS = ["#bbf7d0", "#86efac", "#4ade80", "#16a34a", "#166534"]

function toDate(value) {
	const date = value instanceof Date ? new Date(value) : new Date(`${value}T00:00:00`)
	date.setHours(0, 0, 0, 0)
	return date
}

function toDateString(date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
		date.getDate()
	).padStart(2, "0")}`
}

function addDays(date, days) {
	const next = new Date(date)
	next.setDate(next.getDate() + days)
	return next
}

function startOfWeekMonday(date) {
	const copy = toDate(date)
	const day = copy.getDay() || 7
	return addDays(copy, 1 - day)
}

function getLevelForRatio(ratio) {
	if (ratio <= 0) return 0
	if (ratio < 0.5) return 1
	if (ratio < 0.75) return 2
	if (ratio < 1) return 3
	if (ratio < 1.25) return 4
	return 5
}

function getFallbackHours(status, standardDayHours) {
	if (status === "Half Day") return standardDayHours * 0.5
	if (status === "Present" || status === "Work From Home") return standardDayHours
	return 0
}

function hasAttendance(status, hours) {
	return status === "Present" || status === "Work From Home" || status === "Half Day" || hours > 0
}

export function getAttendanceHeatmapCellMeta({
	event = null,
	date,
	today = new Date(),
	standardDayHours = DEFAULT_STANDARD_DAY_HOURS,
} = {}) {
	const dateValue = toDate(date)
	const todayValue = toDate(today)
	const isFuture = dateValue > todayValue
	const status = event?.attendance || ""
	const hours = Number(event?.working_hours ?? getFallbackHours(status, standardDayHours))

	if (isFuture) {
		return { level: 0, color: NO_ATTENDANCE_COLOR, isFuture: true }
	}

	if (!event || !hasAttendance(status, hours)) {
		return { level: 0, color: NO_ATTENDANCE_COLOR, isFuture: false }
	}

	const level = getLevelForRatio(hours / standardDayHours)
	return {
		level,
		color: level > 0 ? LEVEL_COLORS[level - 1] : EMPTY_COLOR,
		isFuture: false,
	}
}

export function buildRecentWeekdayHeatmap({
	events = {},
	today = new Date(),
	weeks = 13,
	standardDayHours = DEFAULT_STANDARD_DAY_HOURS,
} = {}) {
	const currentWeekStart = startOfWeekMonday(today)
	const firstWeekStart = addDays(currentWeekStart, -(weeks - 1) * 7)
	const cells = []

	for (let week = 0; week < weeks; week++) {
		for (let weekday = 1; weekday <= 7; weekday++) {
			const date = addDays(firstWeekStart, week * 7 + (weekday - 1))
			const dateString = toDateString(date)
			const event = events[dateString] || null
			const meta = getAttendanceHeatmapCellMeta({
				event,
				date: dateString,
				today,
				standardDayHours,
			})

			cells.push({
				date: dateString,
				weekday,
				event,
				...meta,
			})
		}
	}

	return cells
}

function getMonthLabel(dateString, lang) {
	const month = Number(dateString.slice(5, 7))
	if (lang === "en") {
		return new Date(`${dateString}T00:00:00`).toLocaleString("en", { month: "short" })
	}
	return `${month}月`
}

export function buildHeatmapMonthMarkers({ cells = [], lang = "zh", daysPerWeek = 7 } = {}) {
	const weeks = []

	for (let index = 0; index < cells.length; index += daysPerWeek) {
		const cell = cells[index]
		if (cell) weeks.push(cell)
	}

	return weeks.map((cell, index) => {
		const month = cell.date.slice(5, 7)
		const previousMonth = index > 0 ? weeks[index - 1].date.slice(5, 7) : null
		return {
			key: cell.date,
			label: index === 0 || month !== previousMonth ? getMonthLabel(cell.date, lang) : "",
		}
	})
}
