import test from "node:test"
import assert from "node:assert/strict"

import { getAttendanceCopy } from "./attendanceCalendarCopy.js"

test("copy resolves per language", () => {
	assert.equal(getAttendanceCopy("legend.overtime", "zh"), "加班")
	assert.equal(getAttendanceCopy("legend.overtime", "ja"), "残業")
	assert.equal(getAttendanceCopy("legend.overtime", "en"), "Overtime")
})

test("copy falls back to Chinese for an unknown language", () => {
	assert.equal(getAttendanceCopy("legend.rest", "fr"), getAttendanceCopy("legend.rest", "zh"))
	assert.equal(getAttendanceCopy("legend.rest", undefined), getAttendanceCopy("legend.rest", "zh"))
})

test("an unknown key returns itself instead of blank", () => {
	assert.equal(getAttendanceCopy("nope.missing", "zh"), "nope.missing")
})

test("the anomaly notice interpolates the day count", () => {
	assert.equal(getAttendanceCopy("anomaly.notice", "zh", { count: 3 }), "本月有 3 天打卡异常")
	assert.equal(getAttendanceCopy("anomaly.notice", "ja", { count: 3 }), "今月は3日打刻異常があります")
	assert.equal(getAttendanceCopy("anomaly.notice", "en", { count: 3 }), "3 days need attention this month")
})

test("the progress label interpolates both numbers", () => {
	assert.equal(getAttendanceCopy("summary.progress", "zh", { done: 23, total: 26 }), "已出勤 23 / 26 天")
})

test("every key is defined in all three languages", () => {
	const keys = [
		"legend.overtime",
		"legend.anomaly",
		"legend.rest",
		"summary.title",
		"summary.totalHours",
		"summary.workDays",
		"summary.avgHours",
		"summary.progress",
		"anomaly.notice",
		"anomaly.action",
		"badge.rest",
		"badge.holiday",
		"badge.working",
	]
	for (const key of keys) {
		for (const lang of ["zh", "ja", "en"]) {
			const value = getAttendanceCopy(key, lang, { count: 1, done: 1, total: 1 })
			assert.notEqual(value, key, `${key} is missing for ${lang}`)
		}
	}
})
