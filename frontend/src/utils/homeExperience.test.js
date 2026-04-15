import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import {
	getStatusChipMeta,
	getPrimaryScanCopy,
	getBottomTabItems,
	resolveWorkStatusValue,
	getPrimaryScanAction,
	getPrimaryScanMeta,
	getHeroSummaryCopy,
	getRosterEmptyCopy,
} from "./homeExperience.js"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const homeHeroCardPath = path.resolve(currentDir, "../components/home/HomeHeroCard.vue")
const checkInPanelPath = path.resolve(currentDir, "../components/CheckInPanel.vue")

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

test("returns work-state-aware hero summary text", () => {
	assert.equal(getHeroSummaryCopy({ isWorking: false, lang: "zh", timeText: "18:06" }), "上次退勤 18:06")
	assert.equal(getHeroSummaryCopy({ isWorking: true, lang: "zh" }), "今天已出勤，点击可查看今日勤怠")
})

test("keeps the hero state unresolved until attendance and settings are ready", () => {
	const source = fs.readFileSync(checkInPanelPath, "utf8")

	assert.match(source, /if \(checkins\.list\.loading \|\| !checkins\.data\) return null/)
	assert.match(source, /if \(isWorking\.value === null\) return null/)
	assert.match(source, /if \(!isMobileCheckinAllowed\.value\) return null/)
})

test("guards hero summary and CTA rendering behind nullable props", () => {
	const source = fs.readFileSync(homeHeroCardPath, "utf8")

	assert.match(source, /<p\s+v-if="summary"\s+class="hero-summary">/)
	assert.match(source, /<button\s+v-if="cta"\s+type="button"\s+class="hero-cta"/)
	assert.match(source, /summary:\s*\{\s*type:\s*String,\s*default:\s*null/)
	assert.match(source, /cta:\s*\{\s*type:\s*Object,\s*default:\s*null/)
})

test("returns the compressed roster empty copy", () => {
	assert.deepEqual(getRosterEmptyCopy("zh"), {
		today: "今日无班次",
		todayHint: "今天没有已发布排班",
		next: "暂无下个班次",
		nextHint: "后续班次尚未发布",
	})
})
