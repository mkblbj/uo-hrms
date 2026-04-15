import test from "node:test"
import assert from "node:assert/strict"

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
	assert.deepEqual(getStatusChipMeta(false, "ja"), {
		label: "已退勤",
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
