import assert from "node:assert/strict"
import { test } from "node:test"
import { nextTick, ref, watch } from "vue"

import {
	handleLinkOpenUpdate,
	handlePayrollPeriodsSuccess,
	resetLinkSearchState,
	syncSalaryDocuments,
} from "./selectionControlState.js"

function createSalaryDocuments() {
	return {
		data: [{ name: "SAL-OLD" }],
		filters: {
			employee: "EMP-1",
			start_date: ["between", ["2025-01-01", "2025-12-31"]],
		},
		reloadCount: 0,
		reload() {
			this.reloadCount += 1
		},
		setData(data) {
			this.data = data
		},
	}
}

test("resetLinkSearchState cancels pending search before clearing and reloading", () => {
	const query = ref("ali")
	const searchText = ref("ali")
	const events = []

	resetLinkSearchState({
		query,
		searchText,
		cancelPendingSearch() {
			events.push("cancel")
		},
		reloadOptions(value) {
			events.push(["reload", value, query.value, searchText.value])
		},
	})

	assert.equal(query.value, "")
	assert.equal(searchText.value, "")
	assert.deepEqual(events, ["cancel", ["reload", "", "", ""]])
})

test("handleLinkOpenUpdate resets only when the combobox opens", () => {
	let resetCount = 0
	const reset = () => {
		resetCount += 1
	}

	handleLinkOpenUpdate(false, reset)
	handleLinkOpenUpdate(true, reset)

	assert.equal(resetCount, 1)
})

test("same-name payroll refresh applies refreshed dates with one reload", () => {
	const selectedPeriod = ref("FY-2026")
	const periodsByName = {
		"FY-2026": { start_date: "2026-04-01", end_date: "2027-03-31" },
	}
	const documents = createSalaryDocuments()
	const sync = (name) => syncSalaryDocuments(name, periodsByName, documents)

	handlePayrollPeriodsSuccess([{ value: "FY-2026" }], selectedPeriod, sync)

	assert.equal(selectedPeriod.value, "FY-2026")
	assert.deepEqual(documents.filters.start_date, ["between", ["2026-04-01", "2027-03-31"]])
	assert.equal(documents.reloadCount, 1)
})

test("new payroll period relies on the watcher and reloads only once", async () => {
	const selectedPeriod = ref("FY-2025")
	const periodsByName = {
		"FY-2026": { start_date: "2026-04-01", end_date: "2027-03-31" },
	}
	const documents = createSalaryDocuments()
	const sync = (name) => syncSalaryDocuments(name, periodsByName, documents)
	watch(selectedPeriod, sync)

	handlePayrollPeriodsSuccess([{ value: "FY-2026" }], selectedPeriod, sync)
	await nextTick()

	assert.equal(selectedPeriod.value, "FY-2026")
	assert.equal(documents.reloadCount, 1)
})

test("empty payroll periods clear the stale filter and salary data without reloading", async () => {
	const selectedPeriod = ref("FY-2026")
	const documents = createSalaryDocuments()
	const sync = (name) => syncSalaryDocuments(name, {}, documents)
	watch(selectedPeriod, sync)

	handlePayrollPeriodsSuccess([], selectedPeriod, sync)
	await nextTick()

	assert.equal(selectedPeriod.value, "")
	assert.equal("start_date" in documents.filters, false)
	assert.deepEqual(documents.data, [])
	assert.equal(documents.reloadCount, 0)
})
