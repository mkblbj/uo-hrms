import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const componentDir = path.resolve(currentDir, "../../components/work_roster")

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
