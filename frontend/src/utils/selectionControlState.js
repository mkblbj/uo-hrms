const salaryDocumentsState = new WeakMap()

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
	const state = getSalaryDocumentsState(documents)
	const period = periodsByName[periodName]
	if (!period) {
		state.generation += 1
		documents.list.abort()
		delete documents.filters.start_date
		commitSalaryDocuments(state, documents, [])
		return
	}

	documents.filters.start_date = ["between", [period.start_date, period.end_date]]
	reloadSalaryDocuments(documents)
}

export function handleSalaryDocumentsUpdate(periodName, periodsByName, documents) {
	return syncSalaryDocuments(periodName, periodsByName, documents)
}

export function reloadSalaryDocuments(documents) {
	const state = getSalaryDocumentsState(documents)
	documents.list.abort()
	const generation = ++state.generation

	return Promise.resolve(documents.reload()).then(() => {
		if (generation === state.generation) {
			commitSalaryDocuments(state, documents, documents.data)
		} else {
			commitSalaryDocuments(state, documents, state.data)
		}
	})
}

function getSalaryDocumentsState(documents) {
	if (!salaryDocumentsState.has(documents)) {
		salaryDocumentsState.set(documents, {
			generation: 0,
			data: documents.data,
		})
	}
	return salaryDocumentsState.get(documents)
}

function commitSalaryDocuments(state, documents, data) {
	state.data = data
	documents.setData(data)
	documents.commitData?.(data)
}

export function handlePayrollPeriodsSuccess(data, selectedPeriod, syncSelectedPeriod) {
	const nextPeriod = data[0]?.value ?? ""
	if (selectedPeriod.value === nextPeriod) {
		syncSelectedPeriod(nextPeriod)
		return
	}

	selectedPeriod.value = nextPeriod
}
