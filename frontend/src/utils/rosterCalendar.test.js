import test from "node:test"
import assert from "node:assert/strict"

import {
	addRosterMonth,
	buildHomePreferenceGroup,
	buildRosterCalendarCells,
	createRosterRequestGate,
	formatRosterPreferenceTitle,
	getRosterCacheKey,
	getRosterCopy,
	normalizeRosterLanguage,
	resolveRosterFallbackMonth,
	resolveHomePreferenceNotices,
	resolveRosterInitialState,
	shouldCloseRosterSheet,
} from "./rosterCalendar.js"

test("moves roster month across year boundaries", () => {
	assert.deepEqual(addRosterMonth({ year: 2026, month: 1 }, -1), {
		year: 2025,
		month: 12,
	})
	assert.deepEqual(addRosterMonth({ year: 2026, month: 12 }, 1), {
		year: 2027,
		month: 1,
	})
})

test("home lists every month that is collecting preferences", () => {
	const october = { period: "Office-2044-10", status: "Collecting", has_preference: false }
	const december = { period: "Office-2044-12", status: "Collecting", has_preference: true }
	assert.deepEqual(
		resolveHomePreferenceNotices({
			preference_notice: october,
			preference_notices: [october, december],
		}),
		[october, december]
	)
})

test("home preference reminders skip months that are not collecting or have no period", () => {
	const october = { period: "Office-2044-10", status: "Collecting", has_preference: false }
	assert.deepEqual(
		resolveHomePreferenceNotices({
			preference_notices: [
				october,
				{ ...october, period: "Office-2044-11", status: "Scheduling" },
				{ ...october, period: "Office-2044-12", status: "Published" },
				{ ...october, period: "" },
				{ status: "Collecting", has_preference: false },
				null,
			],
		}),
		[october]
	)
	assert.deepEqual(resolveHomePreferenceNotices(null), [])
	assert.deepEqual(resolveHomePreferenceNotices({ preference_notices: [] }), [])
})

test("an older server that sends a single notice still shows it", () => {
	const october = { period: "Office-2044-10", status: "Collecting", has_preference: false }
	assert.deepEqual(resolveHomePreferenceNotices({ preference_notice: october }), [october])
	assert.deepEqual(
		resolveHomePreferenceNotices({ preference_notice: { ...october, status: "Scheduling" } }),
		[]
	)
})

test("localizes the home preference reminder title from structured period data", () => {
	const officeNotice = {
		title: "2026年9月 - 办公室",
		year: 2026,
		month: 9,
		department_category: "Office",
	}
	assert.equal(formatRosterPreferenceTitle(officeNotice, "zh"), "2026年9月 - 办公室")
	assert.equal(formatRosterPreferenceTitle(officeNotice, "ja"), "2026年9月 - 事務")
	assert.equal(formatRosterPreferenceTitle(officeNotice, "en"), "September 2026 - Office")
	assert.equal(
		formatRosterPreferenceTitle({ ...officeNotice, department_category: "Production" }, "ja"),
		"2026年9月 - 生産"
	)
	assert.equal(
		formatRosterPreferenceTitle({ ...officeNotice, department_category: undefined }, "ja"),
		"2026年9月"
	)
	for (const year of [undefined, null, "", " ", 0]) {
		assert.equal(formatRosterPreferenceTitle({ ...officeNotice, year }, "ja"), officeNotice.title)
	}
})

test("defaults bottom-tab entry to mine and honors safe legacy query", () => {
	const now = new Date("2026-07-27T12:00:00+09:00")
	assert.deepEqual(resolveRosterInitialState({ now, query: {} }), {
		scope: "mine",
		year: 2026,
		month: 7,
		legacyPeriod: "",
	})
	assert.deepEqual(
		resolveRosterInitialState({
			now,
			query: {
				view: "department",
				period: "Production-2026-8",
			},
		}),
		{
			scope: "department",
			year: 2026,
			month: 7,
			legacyPeriod: "Production-2026-8",
		}
	)
})

test("keys department cache by selected category and month", () => {
	assert.equal(getRosterCacheKey("mine", 2026, 8), "mine:2026-08")
	assert.equal(getRosterCacheKey("department", 2026, 8, "Office"), "department:Office:2026-08")
	assert.equal(
		getRosterCacheKey("department", 2026, 8, "Production"),
		"department:Production:2026-08"
	)
})

test("builds a complete seven-column month with day data", () => {
	const cells = buildRosterCalendarCells({
		year: 2026,
		month: 8,
		days: [
			{
				date: "2026-08-05",
				my_shift: { scheduled_time: "09:00-18:00" },
			},
		],
		holidays: [
			{
				holiday_date: "2026-08-11",
				description: "山の日",
				weekly_off: 0,
			},
		],
		events: [
			{
				event_date: "2026-08-05",
				title: "セール",
				event_type: "Sale",
			},
		],
		today: "2026-08-05",
	})

	assert.equal(cells.length % 7, 0)
	assert.equal(cells.find((cell) => cell.dateStr === "2026-08-05").isToday, true)
	assert.equal(cells.find((cell) => cell.dateStr === "2026-08-05").day, 5)
	assert.equal(cells[0].empty, true)
	assert.equal(cells.find((cell) => cell.dateStr === "2026-08-05").event.title, "セール")
	assert.equal(cells.find((cell) => cell.dateStr === "2026-08-11").holidayName, "山の日")
})

test("uses fallback only on initial empty month", () => {
	const requested = { year: 2026, month: 8 }
	const response = {
		period: null,
		default_month: { year: 2026, month: 9 },
	}
	assert.deepEqual(
		resolveRosterFallbackMonth({
			requested,
			response,
			initial: true,
		}),
		{ year: 2026, month: 9 }
	)
	assert.equal(
		resolveRosterFallbackMonth({
			requested,
			response,
			initial: false,
		}),
		null
	)
})

test("accepts only the latest monthly request token", () => {
	const gate = createRosterRequestGate()
	const first = gate.begin()
	const second = gate.begin()
	assert.equal(gate.isLatest(first), false)
	assert.equal(gate.isLatest(second), true)
})

test("closes sheet only after a meaningful downward drag", () => {
	assert.equal(shouldCloseRosterSheet(40), false)
	assert.equal(shouldCloseRosterSheet(56), true)
	assert.equal(shouldCloseRosterSheet(-80), false)
})

test("provides complete key labels in zh ja and en", () => {
	assert.equal(getRosterCopy("myShift", "zh"), "我的 Shift")
	assert.equal(getRosterCopy("myShift", "ja"), "私のシフト")
	assert.equal(getRosterCopy("myShift", "en"), "My Shift")
	assert.equal(normalizeRosterLanguage("ja_JP"), "ja")
	assert.equal(normalizeRosterLanguage("en-US"), "en")
	assert.equal(getRosterCopy("scheduledPeople", "ja", { count: 6 }), "実 6人")
	assert.equal(getRosterCopy("departmentSelector", "zh"), "选择部门")
})

const collecting = (period, year, month, has_preference, preference_deadline = null) => ({
	period,
	year,
	month,
	department_category: "Office",
	status: "Collecting",
	has_preference,
	preference_deadline,
})

test("home preference group shows one entry per month with its own state", () => {
	const group = buildHomePreferenceGroup(
		[
			collecting("Office-2026-11", 2026, 11, false, "2026-10-20"),
			collecting("Office-2026-12", 2026, 12, true),
			collecting("Office-2027-01", 2027, 1, false),
		],
		{ lang: "ja", today: "2026-10-12" }
	)
	assert.equal(group.title, "シフト希望")
	assert.deepEqual([group.countText, group.countTone], ["あと2か月分", "pending"])
	assert.deepEqual(
		group.rows.map((row) => [row.period, row.title, row.done, row.actionText, row.deadlineText, row.urgent, row.to]),
		[
			["Office-2026-11", "2026年11月 - 事務", false, "希望を入力", "締切 10/20", false, "/work-roster/preference/Office-2026-11"],
			["Office-2026-12", "2026年12月 - 事務", true, "提出済み", "", false, "/work-roster/preference/Office-2026-12"],
			["Office-2027-01", "2027年1月 - 事務", false, "希望を入力", "", false, "/work-roster/preference/Office-2027-01"],
		]
	)
})

test("two or more months sit side by side as short month tiles; one month stays a full row", () => {
	const group = buildHomePreferenceGroup(
		[
			collecting("Office-2026-11", 2026, 11, false, "2026-10-15"),
			collecting("Office-2026-12", 2026, 12, true, "2026-10-13"),
			collecting("Office-2027-01", 2027, 1, false),
			collecting("Office-2027-02", 2027, 2, false, "2026-11-30"),
		],
		{ lang: "ja", today: "2026-10-12" }
	)
	assert.equal(group.layout, "tiles")
	assert.deepEqual(
		group.rows.map((row) => [row.monthText, row.statusText, row.tone]),
		[
			["11月", "締切 10/15", "urgent"],
			["12月", "提出済み", "done"],
			["1月", "未提出", "pending"],
			["2月", "締切 11/30", "pending"],
		]
	)
	const en = buildHomePreferenceGroup(
		[collecting("A", 2026, 12, true), collecting("B", 2027, 1, false)],
		{ lang: "en", today: "2026-10-12" }
	)
	assert.deepEqual(
		en.rows.map((row) => [row.monthText, row.statusText]),
		[["Dec", "Submitted"], ["Jan", "Not yet"]]
	)
	assert.equal(
		buildHomePreferenceGroup([collecting("A", 2026, 11, false)], { lang: "zh", today: "2026-10-12" }).layout,
		"list"
	)
})

test("home preference group count turns green when every month is submitted and hides for one month", () => {
	const done = buildHomePreferenceGroup(
		[collecting("Office-2026-11", 2026, 11, true), collecting("Office-2026-12", 2026, 12, true)],
		{ lang: "zh", today: "2026-10-12" }
	)
	assert.deepEqual([done.countText, done.countTone], ["已全部提交", "done"])
	const one = buildHomePreferenceGroup([collecting("Office-2026-11", 2026, 11, false)], {
		lang: "en",
		today: "2026-10-12",
	})
	assert.deepEqual([one.countText, one.countTone], ["", ""])
	assert.equal(one.rows[0].actionText, "Submit")
	const single = buildHomePreferenceGroup(
		[collecting("Office-2026-11", 2026, 11, false), collecting("Office-2026-12", 2026, 12, true)],
		{ lang: "zh", today: "2026-10-12" }
	)
	assert.equal(single.countText, "还差 1 个月")
})

test("a deadline within a week is urgent, but only for months not yet submitted", () => {
	const rows = buildHomePreferenceGroup(
		[
			collecting("A", 2026, 11, false, "2026-10-19"),
			collecting("B", 2026, 12, false, "2026-10-20"),
			collecting("C", 2027, 1, false, "2026-10-01"),
			collecting("D", 2027, 2, true, "2026-10-13"),
		],
		{ lang: "en", today: "2026-10-12" }
	).rows
	assert.deepEqual(
		rows.map((row) => [row.deadlineText, row.urgent]),
		[["Due 10/19", true], ["Due 10/20", false], ["Due 10/1", true], ["Due 10/13", false]]
	)
	assert.deepEqual(buildHomePreferenceGroup([], { lang: "ja", today: "2026-10-12" }).rows, [])
})
