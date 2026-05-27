import assert from "node:assert/strict"
import { test } from "node:test"

import * as attendanceCorrection from "./attendanceCorrection.js"

const {
	buildAttendanceCorrectionTabs,
	buildCorrectionPayload,
	buildOriginalCheckinOptions,
	formatCorrectionDateTime,
	getAttendanceCorrectionCopy,
	getCorrectionStatusTheme,
} = attendanceCorrection

test("buildAttendanceCorrectionTabs hides approval tab for non approvers", () => {
	assert.deepEqual(buildAttendanceCorrectionTabs(false, 0, "ja"), [{ key: "mine", label: "打刻修正" }])
})

test("buildAttendanceCorrectionTabs shows approval count for approvers", () => {
	assert.deepEqual(buildAttendanceCorrectionTabs(true, 3, "zh"), [
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
	assert.equal(formatCorrectionDateTime("2026-05-20T09:05:00", "zh"), "2026年5月20日 09:05")
	assert.equal(formatCorrectionDateTime("2026-05-20 18:05:00", "ja"), "2026年5月20日 18:05")
	assert.equal(formatCorrectionDateTime("2026-05-20 18:05:00", "en"), "2026-05-20 18:05")
})

test("buildOriginalCheckinOptions shows only contextual checkins with readable labels", () => {
	assert.deepEqual(
		buildOriginalCheckinOptions(
			[
				{ name: "EMP-CKIN-2026-1", log_type: "IN", time: "2026-05-27 08:56:00" },
				{ name: "EMP-CKIN-2026-2", log_type: "OUT", time: "2026-05-27 18:03:00" },
			],
			"zh"
		),
		[
			{ label: "08:56 上班打卡", value: "EMP-CKIN-2026-1" },
			{ label: "18:03 下班打卡", value: "EMP-CKIN-2026-2" },
		]
	)
})

test("getAttendanceCorrectionCopy returns localized request type and status labels", () => {
	assert.equal(getAttendanceCorrectionCopy("requestType.Correct Checkin Time", "zh"), "修正打卡时间")
	assert.equal(getAttendanceCorrectionCopy("status.Applied", "ja"), "反映済み")
	assert.equal(getAttendanceCorrectionCopy("attendanceStatus.Present", "zh"), "出勤")
	assert.equal(getAttendanceCorrectionCopy("form.submit", "en"), "Submit")
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
