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

// The rows stretch to fill whatever height is left, but never below 56px — the
// attendance page carries a summary card and a notice above the grid, and on a
// 667px-tall screen an unbounded 1fr collapsed the blocks to 4px.
export const MIN_CALENDAR_ROW_HEIGHT = 56

export function getCalendarGridStyle(weekCount) {
	if (!weekCount) return {}
	return {
		gridTemplateRows: `repeat(${weekCount}, minmax(${MIN_CALENDAR_ROW_HEIGHT}px, 1fr))`,
	}
}
