import test from "node:test"
import assert from "node:assert/strict"

import {
	getStatusChipMeta,
	getPrimaryScanCopy,
	getBottomTabItems,
	resolveWorkStatusValue,
	getPrimaryScanAction,
	getPrimaryScanMeta,
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

test("returns null chip metadata until work status is explicitly resolved", () => {
	assert.equal(resolveWorkStatusValue(undefined), null)
	assert.equal(resolveWorkStatusValue({}), null)
	assert.equal(resolveWorkStatusValue({ is_working: true }), true)
	assert.equal(resolveWorkStatusValue({ is_working: false }), false)
	assert.equal(getStatusChipMeta(undefined, "ja"), null)
	assert.equal(getStatusChipMeta(null, "zh"), null)
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
	assert.equal(getPrimaryScanCopy(undefined, "zh"), null)
})

test("derives the scan action and copy from the same work-status input", () => {
	const translate = (value) => `tr:${value}`

	assert.deepEqual(getPrimaryScanAction(false, translate), {
		action: "IN",
		label: "tr:Check In",
	})
	assert.deepEqual(getPrimaryScanAction(true, translate), {
		action: "OUT",
		label: "tr:Check Out",
	})
	assert.equal(getPrimaryScanAction(null, translate), null)

	assert.deepEqual(getPrimaryScanMeta(false, "zh", translate), {
		action: "IN",
		label: "tr:Check In",
		title: "扫码出勤",
		description: "打开相机进行打卡",
	})
	assert.deepEqual(getPrimaryScanMeta(true, "ja", translate), {
		action: "OUT",
		label: "tr:Check Out",
		title: "QRコードで退勤",
		description: "カメラを起動して退勤します",
	})
	assert.equal(getPrimaryScanMeta(undefined, "zh", translate), null)
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
