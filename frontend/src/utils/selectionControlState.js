export function resetLinkSearchState({ query, searchText, cancelPendingSearch, reloadOptions }) {
	cancelPendingSearch()
	query.value = ""
	searchText.value = ""
	reloadOptions("")
}

export function handleLinkOpenUpdate(isOpen, resetSearch) {
	if (isOpen) resetSearch()
}

export function syncSalaryDocuments(periodName, periodsByName, documents) {
	const period = periodsByName[periodName]
	if (!period) {
		delete documents.filters.start_date
		documents.setData([])
		return
	}

	documents.filters.start_date = ["between", [period.start_date, period.end_date]]
	documents.reload()
}

export function handlePayrollPeriodsSuccess(data, selectedPeriod, syncSelectedPeriod) {
	const nextPeriod = data[0]?.value ?? ""
	if (selectedPeriod.value === nextPeriod) {
		syncSelectedPeriod(nextPeriod)
		return
	}

	selectedPeriod.value = nextPeriod
}
