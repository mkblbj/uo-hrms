import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const componentDir = path.resolve(currentDir, "../../components/work_roster")
const dashboardPath = path.resolve(currentDir, "Dashboard.vue")

function readComponent(name) {
	return fs.readFileSync(path.join(componentDir, name), "utf8")
}

test("roster tabs expose accessible selected state", () => {
	const source = readComponent("RosterViewTabs.vue")
	assert.match(source, /role="tablist"/)
	assert.match(source, /role="tab"/)
	assert.match(source, /aria-selected/)
	assert.match(source, /update:modelValue/)
})

test("preference banner keeps existing preference route", () => {
	const source = readComponent("RosterPreferenceBanner.vue")
	assert.match(source, /work-roster\/preference/)
	assert.match(source, /notice\.status/)
	assert.match(source, /notice\.has_preference/)
})

test("month header has named previous and next controls", () => {
	const source = readComponent("RosterMonthHeader.vue")
	assert.match(source, /aria-label/)
	assert.match(source, /emit\(["']previous["']\)/)
	assert.match(source, /emit\(["']next["']\)/)
})

test("calendar is a seven-column non-scrolling grid", () => {
	const source = readComponent("RosterMonthCalendar.vue")
	assert.match(source, /grid-template-columns:\s*repeat\(7/)
	assert.doesNotMatch(source, /overflow-x:\s*(auto|scroll)/)
	assert.match(source, /focusDate/)
})

test("day cell separates mine and department summaries", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /scope === ["']mine["']/)
	assert.match(source, /actual_count/)
	assert.match(source, /equivalent_count/)
	assert.match(source, /departmentCategory === ["']Production["']/)
})

test("day sheet is modal, safe-area aware, and excludes attendance", () => {
	const source = readComponent("RosterDaySheet.vue")
	assert.match(source, /role="dialog"/)
	assert.match(source, /aria-modal="true"/)
	assert.match(source, /safe-area-inset-bottom/)
	assert.match(source, /employees/)
	assert.doesNotMatch(source, /in_time|out_time|working_hours|attendanceResource/)
})

test("dashboard uses the mobile roster api and shared components", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /get_mobile_roster_calendar/)
	assert.match(source, /RosterViewTabs/)
	assert.match(source, /RosterPreferenceBanner/)
	assert.match(source, /RosterMonthHeader/)
	assert.match(source, /RosterMonthCalendar/)
	assert.match(source, /RosterDaySheet/)
})

test("dashboard does not request attendance or render period cards", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.doesNotMatch(source, /get_attendance_calendar_events|attendanceResource/)
	assert.doesNotMatch(source, /v-for="period in dashboardData/)
	assert.doesNotMatch(source, /upcoming_entries/)
})

test("dashboard has no-employee unpublished failure and retry states", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /no_employee/)
	assert.match(source, /periodMissing/)
	assert.match(source, /loadError/)
	assert.match(source, /retry/)
})
