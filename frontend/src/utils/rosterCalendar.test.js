import test from "node:test"
import assert from "node:assert/strict"

import {
	addRosterMonth,
	buildRosterCalendarCells,
	createRosterRequestGate,
	getRosterCacheKey,
	getRosterCopy,
	normalizeRosterLanguage,
	resolveRosterFallbackMonth,
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

test("keys cache by scope and month", () => {
	assert.equal(getRosterCacheKey("mine", 2026, 8), "mine:2026-08")
	assert.equal(getRosterCacheKey("department", 2026, 8), "department:2026-08")
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
})
