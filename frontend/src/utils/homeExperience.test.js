import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

import * as homeExperience from "./homeExperience.js"
import {
	getStatusChipMeta,
	getPrimaryScanCopy,
	getBottomTabItems,
	resolveWorkStatusValue,
	resolveHomeLanguage,
	getPrimaryScanAction,
	getPrimaryScanMeta,
	getHeroCardMeta,
	getHeroSummaryCopy,
	getRosterEmptyCopy,
} from "./homeExperience.js"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const homeHeroCardPath = path.resolve(currentDir, "../components/home/HomeHeroCard.vue")
const checkInPanelPath = path.resolve(currentDir, "../components/CheckInPanel.vue")
const weatherWidgetPath = path.resolve(currentDir, "../components/WeatherWidget.vue")
const homeViewPath = path.resolve(currentDir, "../views/Home.vue")
const homeSummaryCardPath = path.resolve(
	currentDir,
	"../components/work_roster/HomeSummaryCard.vue",
)

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

test("emits and unbinds the check-in status refresh contract on EventTarget", () => {
	assert.equal(typeof homeExperience.emitCheckinStatusChanged, "function")
	assert.equal(typeof homeExperience.bindCheckinStatusRefresh, "function")

	const target = new EventTarget()
	const receivedDetails = []
	const unbind = homeExperience.bindCheckinStatusRefresh(target, (event) => {
		receivedDetails.push(event.detail)
	})

	assert.equal(typeof unbind, "function")
	homeExperience.emitCheckinStatusChanged(target, { log_type: "OUT" })
	assert.deepEqual(receivedDetails, [{ log_type: "OUT" }])

	unbind()
	homeExperience.emitCheckinStatusChanged(target, { log_type: "IN" })
	assert.deepEqual(receivedDetails, [{ log_type: "OUT" }])
})

test("resolves the shared home language from boot lang variants and fallbacks", () => {
	assert.equal(resolveHomeLanguage({ lang: "ja_JP" }), "ja")
	assert.equal(resolveHomeLanguage({ lang: "en-US" }), "en")
	assert.equal(resolveHomeLanguage({ server_lang: "ja-JP" }), "ja")
	assert.equal(resolveHomeLanguage({ lang: "fr", server_lang: "en-US" }), "en")
	assert.equal(resolveHomeLanguage({}), "zh")
	assert.equal(resolveHomeLanguage(), "zh")
})

test("returns the working hero summary branch from workStatus.status", () => {
	assert.equal(
		getHeroSummaryCopy({
			workStatus: {
				status: "working",
				is_working: false,
				last_checkin: { log_type: "IN", time: "2026-04-15 09:12:00" },
			},
			lang: "zh",
			hasCta: true,
			formatLastCheckin: () => "should-not-be-used",
		}),
		"今天已出勤，可点击扫码退勤",
	)
})

test("returns the off-work hero summary branch from workStatus.status and last_checkin", () => {
	assert.equal(
		getHeroSummaryCopy({
			workStatus: {
				status: "off_work",
				is_working: true,
				last_checkin: { log_type: "OUT", time: "2026-04-15 18:06:00" },
			},
			lang: "zh",
			hasCta: true,
			formatLastCheckin: (value) =>
				value === "2026-04-15 18:06:00" ? "18:06" : value,
		}),
		"上次退勤 18:06，可点击扫码出勤",
	)
})

test("returns the no-checkin hero summary branch from workStatus.status", () => {
	assert.equal(
		getHeroSummaryCopy({
			workStatus: {
				status: "no_checkin_today",
				is_working: true,
				last_checkin: null,
			},
			lang: "zh",
			hasCta: true,
		}),
		"暂无打卡记录，可点击扫码出勤",
	)
})

test("returns a null hero summary while work status is unresolved", () => {
	assert.equal(getHeroSummaryCopy({ workStatus: null, lang: "zh", hasCta: true }), null)
	assert.equal(getHeroSummaryCopy({ workStatus: undefined, lang: "zh", hasCta: false }), null)
})

test("builds hero state directly from status and last_checkin", () => {
	const translate = (value) => `tr:${value}`

	assert.deepEqual(
		getHeroCardMeta({
			workStatus: undefined,
			lang: "zh",
			allowPrimaryScan: true,
			translate,
		}),
		{
			summary: null,
			cta: null,
		},
	)

	const workingHero = getHeroCardMeta({
		workStatus: {
			status: "working",
			is_working: false,
			last_checkin: { log_type: "IN", time: "2026-04-15 09:12:00" },
		},
		lang: "zh",
		allowPrimaryScan: true,
		translate,
		formatLastCheckin: (value) =>
			value === "2026-04-15 09:12:00" ? "09:12" : value,
	})
	assert.equal(workingHero.summary, "今天已出勤，可点击扫码退勤")
	assert.deepEqual(workingHero.cta, {
		action: "OUT",
		label: "tr:Check Out",
		title: "扫码退勤",
		description: "打开相机完成退勤",
	})

	const offHero = getHeroCardMeta({
		workStatus: {
			status: "off_work",
			is_working: true,
			last_checkin: { log_type: "OUT", time: "2026-04-15 18:06:00" },
		},
		lang: "zh",
		allowPrimaryScan: true,
		translate,
		formatLastCheckin: (value) =>
			value === "2026-04-15 18:06:00" ? "18:06" : value,
	})
	assert.equal(offHero.summary, "上次退勤 18:06，可点击扫码出勤")
	assert.deepEqual(offHero.cta, {
		action: "IN",
		label: "tr:Check In",
		title: "扫码出勤",
		description: "打开相机进行打卡",
	})

	assert.deepEqual(
		getHeroCardMeta({
			workStatus: {
				status: "no_checkin_today",
				is_working: true,
				last_checkin: null,
			},
			lang: "zh",
			allowPrimaryScan: false,
			translate,
		}),
		{
			summary: "暂无打卡记录",
			cta: null,
		},
	)
})

test("CheckInPanel reuses the shared hero state helper without reading checkins for hero copy", () => {
	const source = fs.readFileSync(checkInPanelPath, "utf8")

	assert.match(source, /getHeroCardMeta/)
	assert.doesNotMatch(source, /const lastLog = computed\(/)
	assert.doesNotMatch(source, /timeText:\s*/)
})

test("CheckInPanel drops the legacy list, modal, and socket refresh chain", () => {
	const source = fs.readFileSync(checkInPanelPath, "utf8")

	assert.doesNotMatch(source, /createListResource/)
	assert.doesNotMatch(source, /checkins\.reload\(/)
	assert.doesNotMatch(source, /list_update/)
	assert.doesNotMatch(source, /open-checkin-modal/)
	assert.doesNotMatch(source, /submitLog\(/)
	assert.doesNotMatch(source, /modalController/)
	assert.doesNotMatch(source, /\bIonModal\b/)

	assert.match(source, /QRScannerModal/)
	assert.match(source, /openQRScanner/)
	assert.match(source, /handleQRScanSuccess/)
	assert.match(source, /emitCheckinStatusChanged/)
	assert.doesNotMatch(source, /window\.dispatchEvent/)
})

test("Home owns a single work-status resource shared by the chip and panel", () => {
	const homeSource = fs.readFileSync(homeViewPath, "utf8")
	const chipSource = fs.readFileSync(
		path.resolve(currentDir, "../components/home/HomeStatusChip.vue"),
		"utf8",
	)
	const panelSource = fs.readFileSync(checkInPanelPath, "utf8")

	assert.match(homeSource, /const workStatus = createResource\(/)
	assert.match(homeSource, /<HomeStatusChip\s+:work-status="workStatus"/)
	assert.match(homeSource, /<CheckInPanel\s+class="w-full flex-1"\s+:work-status="workStatus"/)
	assert.doesNotMatch(chipSource, /createResource\(/)
	assert.doesNotMatch(panelSource, /url:\s*"hrms\.api\.get_employee_work_status"/)
})

test("Home wires the shared check-in refresh helper instead of inline event listeners", () => {
	const source = fs.readFileSync(homeViewPath, "utf8")

	assert.match(source, /bindCheckinStatusRefresh/)
	assert.match(source, /unbindCheckinStatusRefresh/)
	assert.doesNotMatch(source, /addEventListener\(\s*["']checkin-status-changed["']/)
	assert.doesNotMatch(source, /removeEventListener\(\s*["']checkin-status-changed["']/)
})

test("keeps the hero state unresolved until work status is explicitly available", () => {
	const source = fs.readFileSync(checkInPanelPath, "utf8")

	assert.match(source, /workStatus:\s*props\.workStatus\?\.data/)
	assert.match(source, /allowPrimaryScan:\s*isMobileCheckinAllowed\.value/)
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

test("returns ja and en home copy branches without mixed-language fallbacks", () => {
	assert.equal(
		getHeroSummaryCopy({
			workStatus: {
				status: "working",
				last_checkin: { log_type: "IN", time: "2026-04-15 09:12:00" },
			},
			lang: "ja",
			hasCta: true,
		}),
		"本日は出勤済みです。タップしてQRコードで退勤できます",
	)
	assert.equal(
		getHeroSummaryCopy({
			workStatus: {
				status: "no_checkin_today",
				last_checkin: null,
			},
			lang: "en",
			hasCta: false,
		}),
		"No attendance record yet.",
	)
	assert.deepEqual(getRosterEmptyCopy("en"), {
		today: "No shift today",
		todayHint: "No published shift today",
		next: "No next shift yet",
		nextHint: "Upcoming shifts are not published yet",
	})
})

test("HomeSummaryCard keeps roster empty copy in a single source", () => {
	const source = fs.readFileSync(homeSummaryCardPath, "utf8")

	assert.match(
		source,
		/import\s+\{\s*getRosterEmptyCopy\s*,\s*resolveHomeLanguage\s*\}\s+from\s+"@\/utils\/homeExperience"/,
	)
	assert.doesNotMatch(source, /\btodayEmpty:\s*\{/)
	assert.doesNotMatch(source, /\btodayEmptyHint:\s*\{/)
	assert.doesNotMatch(source, /\bnextEmpty:\s*\{/)
	assert.doesNotMatch(source, /\bnextEmptyHint:\s*\{/)
})

test("home modules share one language helper instead of local fallbacks", () => {
	const panelSource = fs.readFileSync(checkInPanelPath, "utf8")
	const weatherSource = fs.readFileSync(weatherWidgetPath, "utf8")
	const summarySource = fs.readFileSync(homeSummaryCardPath, "utf8")
	const chipSource = fs.readFileSync(
		path.resolve(currentDir, "../components/home/HomeStatusChip.vue"),
		"utf8",
	)

	assert.match(panelSource, /resolveHomeLanguage/)
	assert.match(panelSource, /<HomeSummaryCard\s+:lang="currentLanguage"/)
	assert.match(panelSource, /<WeatherWidget\s+:lang="currentLanguage"/)
	assert.doesNotMatch(panelSource, /frappe\.boot(?:\?\.|\.?)lang/)

	assert.match(weatherSource, /resolveHomeLanguage/)
	assert.match(weatherSource, /currentLanguage/)
	assert.doesNotMatch(weatherSource, /\|\|\s*["'](?:ja|zh|en)["']/)
	assert.doesNotMatch(weatherSource, /frappe\.boot(?:\?\.|\.?)lang/)

	assert.match(summarySource, /resolveHomeLanguage/)
	assert.match(summarySource, /currentLanguage/)
	assert.doesNotMatch(summarySource, /\|\|\s*["'](?:ja|zh|en)["']/)
	assert.doesNotMatch(summarySource, /frappe\.boot(?:\?\.|\.?)lang/)

	assert.match(chipSource, /resolveHomeLanguage/)
	assert.doesNotMatch(chipSource, /frappe\.boot(?:\?\.|\.?)lang/)
})
