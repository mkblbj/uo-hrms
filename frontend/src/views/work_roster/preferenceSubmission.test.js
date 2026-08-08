import test from "node:test"
import assert from "node:assert/strict"
import {
	buildPreferenceDetails,
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
