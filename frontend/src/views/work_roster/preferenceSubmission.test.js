import test from "node:test"
import assert from "node:assert/strict"
import {
	buildPreferenceDetails,
	canEditPreference,
	shouldShowAutoScheduleNotice,
} from "./preferenceSubmission.js"

test("only selected dates are serialized once", () => {
	const details = buildPreferenceDetails([
		{ date: "2045-09-01", wr_shift_slot: "9-18" },
		{ date: "2045-09-02", wr_shift_slot: "10-19" },
	])
	assert.deepEqual(details.map((row) => row.date), ["2045-09-01", "2045-09-02"])
})

test("auto scheduling notice is production only", () => {
	assert.equal(shouldShowAutoScheduleNotice({ department_category: "Production" }), true)
	assert.equal(shouldShowAutoScheduleNotice({ department_category: "Office" }), false)
})

test("only Collecting periods allow preference edits for both department categories", () => {
	const cases = [
		[{ status: "Collecting", department_category: "Production" }, true],
		[{ status: "Collecting", department_category: "Office" }, true],
		[{ status: "Scheduling", department_category: "Production" }, false],
		[{ status: "Published", department_category: "Office" }, false],
		[null, false],
	]

	for (const [period, expected] of cases) {
		assert.equal(canEditPreference(period), expected)
	}
})
