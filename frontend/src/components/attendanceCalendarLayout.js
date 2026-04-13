export function padCalendarDaysToFullWeeks(days) {
	const paddedDays = [...days]
	while (paddedDays.length > 0 && paddedDays.length % 7 !== 0) {
		paddedDays.push({ empty: true })
	}
	return paddedDays
}

export function getCalendarWeekCount(days) {
	if (!days.length) return 0
	return Math.ceil(days.length / 7)
}

export function getCalendarGridStyle(weekCount) {
	if (!weekCount) return {}
	return {
		gridTemplateRows: `repeat(${weekCount}, minmax(0, 1fr))`,
	}
}
