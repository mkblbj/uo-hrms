import assert from "node:assert/strict"
import { test } from "node:test"

import {
	buildAttendanceCorrectionTabs,
	buildCorrectionPayload,
	formatCorrectionDateTime,
	getCorrectionStatusTheme,
} from "./attendanceCorrection.js"

test("buildAttendanceCorrectionTabs hides approval tab for non approvers", () => {
	assert.deepEqual(buildAttendanceCorrectionTabs(false, 0), [{ key: "mine", label: "补卡申请" }])
})

test("buildAttendanceCorrectionTabs shows approval count for approvers", () => {
	assert.deepEqual(buildAttendanceCorrectionTabs(true, 3), [
		{ key: "mine", label: "补卡申请" },
		{ key: "approvals", label: "待我审批 3" },
	])
})

test("getCorrectionStatusTheme maps statuses", () => {
	assert.equal(getCorrectionStatusTheme("Pending"), "orange")
	assert.equal(getCorrectionStatusTheme("Applied"), "green")
	assert.equal(getCorrectionStatusTheme("Rejected"), "red")
	assert.equal(getCorrectionStatusTheme("Apply Failed"), "red")
	assert.equal(getCorrectionStatusTheme("Draft"), "gray")
})

test("formatCorrectionDateTime returns stable empty value", () => {
	assert.equal(formatCorrectionDateTime(""), "")
	assert.equal(formatCorrectionDateTime(null), "")
})

test("formatCorrectionDateTime normalizes iso-like values for display", () => {
	assert.equal(formatCorrectionDateTime("2026-05-20T09:05:00"), "2026-05-20 09:05")
	assert.equal(formatCorrectionDateTime("2026-05-20 18:05:00"), "2026-05-20 18:05")
})

test("buildCorrectionPayload trims reason and keeps selected original checkin", () => {
	assert.deepEqual(
		buildCorrectionPayload({
			attendance_date: "2026-05-20",
			request_type: "Correct Checkin Time",
			requested_log_type: "OUT",
			requested_time: "2026-05-20 18:05:00",
			original_checkin: "EMP-CKIN-1",
			reason: "  Forgot to scan  ",
		}),
		{
			attendance_date: "2026-05-20",
			request_type: "Correct Checkin Time",
			requested_log_type: "OUT",
			requested_time: "2026-05-20 18:05:00",
			original_checkin: "EMP-CKIN-1",
			reason: "Forgot to scan",
		}
	)
})
