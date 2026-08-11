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

test("month header has navigation and a native department selector", () => {
	const source = readComponent("RosterMonthHeader.vue")
	assert.match(source, /aria-label/)
	assert.match(source, /emit\(["']previous["']\)/)
	assert.match(source, /emit\(["']next["']\)/)
	assert.match(source, /<select/)
	assert.match(source, /selectableDepartment/)
	assert.match(source, /departmentSelector/)
	assert.match(source, /update:departmentCategory/)
})

test("calendar is a seven-column grid that fills the available height", () => {
	const source = readComponent("RosterMonthCalendar.vue")
	assert.match(source, /grid-template-columns:\s*repeat\(7/)
	assert.doesNotMatch(source, /overflow-x:\s*(auto|scroll)/)
	assert.match(source, /focusDate/)
	assert.match(source, /--roster-week-count/)
	assert.match(source, /grid-template-rows:\s*repeat\(var\(--roster-week-count\)/)
	assert.match(source, /flex:\s*1/)
	assert.doesNotMatch(source, /aspect-ratio:\s*0\.78/)
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
	assert.match(source, /RosterMonthHeader/)
	assert.match(source, /RosterMonthCalendar/)
	assert.match(source, /RosterDaySheet/)
})

test("dashboard requests and caches the selected department category", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /selectedDepartmentCategory/)
	assert.match(source, /department_category:\s*requestedDepartmentCategory/)
	assert.match(source, /getRosterCacheKey\([\s\S]*selectedDepartmentCategory/)
	assert.match(source, /@update:department-category/)
})

test("dashboard fills the content area without bottom spacer", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /\.roster-page\s*\{[\s\S]*flex:\s*1/)
	assert.match(source, /\.roster-page\s*\{[\s\S]*min-height:\s*100%/)
	assert.doesNotMatch(source, /calc\(96px \+ env\(safe-area-inset-bottom\)\)/)
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

test("dashboard resolves legacy period through the restricted api", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /resolve_mobile_roster_period/)
	assert.match(source, /initialState\.legacyPeriod/)
	assert.doesNotMatch(source, /frappe\.client\.get/)
})

test("day cell puts the shift time in a centered primary block", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /class="roster-primary"/)
	assert.match(source, /\.roster-primary\s*\{[\s\S]*?flex:\s*1/)
	assert.match(source, /\.roster-primary\s*\{[\s\S]*?justify-content:\s*center/)
	assert.match(source, /\.roster-primary\s*\{[\s\S]*?font-size:\s*clamp\(13px, 4\.1vw, 18px\)/)
})

// A 320px-wide phone gives each cell about 29px of inner width, where even 14px
// digits clip. The narrow breakpoint drops the primary text to a fixed 13px.
test("day cell shrinks the primary text on the narrowest phones", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /@media \(max-width: 340px\)[\s\S]*?\.roster-primary\s*\{[\s\S]*?font-size:\s*13px/)
})

// The primary block is a flex column, so ellipsis has to live on an inner span —
// a bare text node would be clipped mid-glyph instead.
test("day cell truncates long shift times with an ellipsis", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /class="roster-primary-value"/)
	assert.match(source, /\.roster-primary-value\s*\{[\s\S]*?text-overflow:\s*ellipsis/)
	assert.match(source, /\.roster-primary-value\s*\{[\s\S]*?white-space:\s*nowrap/)
})

// 56px row floors overflowed six-week months on 320x568 screens, hiding the last
// row behind the tab bar. 44px keeps the WCAG target without breaking layout —
// when space allows, 1fr already stretches rows well past either floor.
test("day cell keeps a 44px floor so six-week months fit short screens", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /\.roster-day\s*\{[\s\S]*?min-height:\s*44px/)
})

test("day cell fills rest and empty days with a tinted block", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /roster-primary blank/)
	assert.match(source, /\.roster-primary\.blank\s*\{[\s\S]*?background:\s*var\(--h-chip-off-bg/)
	assert.match(source, /labels\.rest/)
	assert.match(source, /labels\.emptyShort/)
})

test("day cell renders events as a chip without the top rule", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /\.roster-day-event\s*\{[\s\S]*?background:\s*var\(--h-summary-warn-bg/)
	assert.match(source, /\.roster-day-event\s*\{[\s\S]*?border-radius:/)
	assert.doesNotMatch(source, /border-top:\s*3px/)
	assert.doesNotMatch(source, /roster-event-color/)
})

test("day cell keeps the date number subordinate to the shift time", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /\.roster-day-number\s*\{[\s\S]*?font-size:\s*clamp\(12px, 3\.2vw, 14px\)/)
	assert.doesNotMatch(source, /font-weight:\s*750/)
})

test("department cell shows the head count above a smaller unit line", () => {
	const source = readComponent("RosterDayCell.vue")
	assert.match(source, /<small/)
	assert.match(source, /labels\.equivalentShort/)
	assert.match(source, /labels\.actualShort/)
	assert.match(source, /\.roster-primary small\s*\{[\s\S]*?font-size:\s*clamp\(10px, 2\.7vw, 12px\)/)
})

test("calendar rows and gaps match the day cells", () => {
	const source = readComponent("RosterMonthCalendar.vue")
	assert.match(
		source,
		/grid-template-rows:\s*repeat\(var\(--roster-week-count\),\s*minmax\(44px,\s*1fr\)\)/
	)
	assert.match(source, /\.roster-weekdays,\s*\.roster-days\s*\{[\s\S]*?gap:\s*4px/)
	assert.match(source, /\.roster-empty-cell\s*\{[\s\S]*?min-height:\s*44px/)
})

test("dashboard trims the gap below the calendar", () => {
	const source = fs.readFileSync(dashboardPath, "utf8")
	assert.match(source, /padding:\s*12px 12px calc\(8px \+ env\(safe-area-inset-bottom\)\)/)
	assert.match(source, /\.roster-skeleton\s*\{[\s\S]*?gap:\s*4px/)
})
