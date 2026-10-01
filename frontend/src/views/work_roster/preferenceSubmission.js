export function buildPreferenceDetails(selectedDates) {
	return selectedDates.map((selection) => ({
		date: selection.date,
		wr_shift_slot: selection.wr_shift_slot,
		custom_start_time: selection.custom_start_time,
		custom_end_time: selection.custom_end_time,
		is_custom: selection.is_custom || 0,
	}))
}

export function shouldShowAutoScheduleNotice(period) {
	return period?.department_category === "Production"
}

export function canEditPreference(period) {
	return period?.status === "Collecting"
}
