import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

import {
	getStatusChipMeta,
	getPrimaryScanCopy,
	getBottomTabItems,
} from "./homeExperience.js"

test("returns working and off-work chip metadata for zh and ja", () => {
	assert.deepEqual(getStatusChipMeta(true, "zh"), {
		label: "正在出勤",
		tone: "working",
		routeName: "AttendanceDashboard",
	})
	assert.deepEqual(getStatusChipMeta(true, "ja"), {
		label: "勤務中",
		tone: "working",
		routeName: "AttendanceDashboard",
	})
	assert.deepEqual(getStatusChipMeta(false, "ja"), {
		label: "退勤済",
		tone: "off",
		routeName: "AttendanceDashboard",
	})
})

test("returns the primary scan CTA copy for both work states", () => {
	assert.deepEqual(getPrimaryScanCopy(false, "zh"), {
		title: "扫码出勤",
		description: "打开相机进行打卡",
	})
	assert.deepEqual(getPrimaryScanCopy(true, "zh"), {
		title: "扫码退勤",
		description: "打开相机完成退勤",
	})
})

test("returns localized bottom-tab labels without mixed-language fallbacks", () => {
	assert.deepEqual(getBottomTabItems("ja").map((item) => item.title), [
		"ホーム",
		"勤怠",
		"シフト",
		"経費",
		"給与",
	])
})

test("CheckInPanel reuses the shared primary scan copy helper", () => {
	const source = readFileSync(new URL("../components/CheckInPanel.vue", import.meta.url), "utf8")

	assert.match(source, /getPrimaryScanCopy/)
	assert.doesNotMatch(source, /function getCheckinButtonText\(/)
	assert.doesNotMatch(source, /function getCheckinButtonDesc\(/)
})

test("Home owns a single work-status resource shared by the chip and panel", () => {
	const homeSource = readFileSync(new URL("../views/Home.vue", import.meta.url), "utf8")
	const chipSource = readFileSync(new URL("../components/home/HomeStatusChip.vue", import.meta.url), "utf8")
	const panelSource = readFileSync(new URL("../components/CheckInPanel.vue", import.meta.url), "utf8")

	assert.match(homeSource, /const workStatus = createResource\(/)
	assert.match(homeSource, /<HomeStatusChip\s+:work-status="workStatus"/)
	assert.match(homeSource, /<CheckInPanel\s+class="w-full flex-1"\s+:work-status="workStatus"/)
	assert.doesNotMatch(chipSource, /createResource\(/)
	assert.doesNotMatch(panelSource, /url:\s*"hrms\.api\.get_employee_work_status"/)
})
