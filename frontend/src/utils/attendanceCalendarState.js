import { hasAttendanceAnomaly } from "./attendanceAnomaly.js"

export const OVERTIME_HOURS = 10

const STATUS_TO_STATE = {
	Present: "work",
	"Work From Home": "wfh",
	"Half Day": "half",
	"On Leave": "leave",
	// Absent is shown as rest until the business separates absence from time off.
	Absent: "rest",
	Holiday: "holiday",
}

const DAY_WEIGHT = { work: 1, wfh: 1, half: 0.5 }

function round1(value) {
	return Math.round(value * 10) / 10
}

export function deriveAttendanceState(attendanceEntry, holiday) {
	if (hasAttendanceAnomaly(attendanceEntry?.anomaly)) return "anomaly"
	const mapped = STATUS_TO_STATE[attendanceEntry?.attendance]
	if (mapped) return mapped
	if (holiday && !holiday.weekly_off) return "holiday"
	if (holiday?.weekly_off) return "rest"
	return "empty"
}

export function isOvertime(hours) {
	return Number.isFinite(hours) && hours >= OVERTIME_HOURS
}

export function formatWorkHours(hours) {
	if (!Number.isFinite(hours) || hours <= 0) return ""
	const rounded = round1(hours)
	return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
}

export function summarizeMonth(cells) {
	let workDays = 0
	let hours = 0
	for (const cell of cells) {
		const weight = DAY_WEIGHT[cell.state]
		if (!weight) continue
		workDays += weight
		hours += cell.hours || 0
	}
	return {
		workDays: round1(workDays),
		hours: round1(hours),
		avg: workDays ? round1(hours / workDays) : 0,
	}
}

export function computeProgress(cells, scheduledDays) {
	const { workDays } = summarizeMonth(cells)
	const total = Number.isFinite(scheduledDays) ? scheduledDays : 0
	if (total <= 0) return { visible: false, done: workDays, total: 0, percent: 0 }
	return {
		visible: true,
		done: workDays,
		total,
		percent: Math.min(100, Math.round((workDays / total) * 100)),
	}
}
