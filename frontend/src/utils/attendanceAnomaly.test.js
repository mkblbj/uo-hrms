import test from "node:test"
import assert from "node:assert/strict"

import {
	ATTENDANCE_ANOMALY_COLOR,
	getAttendanceAnomalyLabel,
	hasAttendanceAnomaly,
} from "./attendanceAnomaly.js"

test("detects attendance anomaly payloads", () => {
	assert.equal(ATTENDANCE_ANOMALY_COLOR, "#dc2626")
	assert.equal(hasAttendanceAnomaly({ has_issue: true, codes: ["missing_checkout"] }), true)
	assert.equal(hasAttendanceAnomaly({ has_issue: false, codes: [] }), false)
	assert.equal(hasAttendanceAnomaly(null), false)
})

test("returns localized anomaly labels from codes", () => {
	assert.equal(
		getAttendanceAnomalyLabel({ has_issue: true, codes: ["missing_checkout"] }, "zh"),
		"缺少签退",
	)
	assert.equal(
		getAttendanceAnomalyLabel({ has_issue: true, codes: ["missing_checkin"] }, "ja"),
		"出勤打刻がありません",
	)
	assert.equal(
		getAttendanceAnomalyLabel({ has_issue: true, codes: ["invalid_sequence"] }, "en"),
		"Invalid check-in sequence",
	)
	assert.equal(getAttendanceAnomalyLabel(null, "zh"), "")
})
