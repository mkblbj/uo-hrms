import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const currentDir = path.dirname(fileURLToPath(import.meta.url))

function read(name) {
	return fs.readFileSync(path.join(currentDir, name), "utf8")
}

test("day cell paints every state with an attendance token", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /--h-attn-work-bg/)
	assert.match(source, /--h-attn-overtime-bg/)
	assert.match(source, /--h-attn-anomaly-bg/)
	assert.match(source, /--h-attn-rest-bg/)
	assert.match(source, /--h-attn-holiday-bg/)
})

// The event row is reserved on every cell so the block below starts at the same
// height whether or not the day carries an event.
test("day cell reserves the event row when there is no event", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /is-spacer/)
	assert.match(source, /\.attn-event\.is-spacer\s*\{[\s\S]*?visibility:\s*hidden/)
})

test("day cell reuses the roster event chip tokens", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /--h-roster-event-bg/)
	assert.match(source, /--h-roster-event-fg/)
})

test("day cell writes the worked hours into the block", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /formatWorkHours/)
	assert.match(source, /isOvertime/)
})

// Clocking in at 09:00 leaves hours at 0 until checkout; falling back to the
// rest label would tell today's user they are off work.
test("day cell never labels an in-progress work day as rest", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /badge\.working/)
	assert.doesNotMatch(source, /formatWorkHours\(props\.cell\.hours\)\s*\|\|\s*getAttendanceCopy\("badge\.rest"/)
})

// anomaly_label is a sentence like "退勤なし"; at the cell's 36px it clips to an
// ellipsis. The dialog already shows the full reason via dlg-anomaly-reason.
test("day cell shows the short anomaly label, not the full reason", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /kind === "anomaly"\) return getAttendanceCopy\("legend\.anomaly"/)
	assert.doesNotMatch(source, /anomaly_label/)
})

test("day cell drops the dots and the roster state", () => {
	const source = read("AttendanceDayCell.vue")
	assert.doesNotMatch(source, /sale-event-dot|weekend-dot/)
	assert.doesNotMatch(source, /state-roster|"roster"|'roster'/)
})

test("day cell stays a focusable button with a large enough target", () => {
	const source = read("AttendanceDayCell.vue")
	assert.match(source, /<button/)
	assert.match(source, /defineExpose\(\{\s*focus\s*\}\)/)
	assert.match(source, /min-height:\s*44px/)
})

test("attendance tokens are defined for both themes", () => {
	const tokens = fs.readFileSync(path.resolve(currentDir, "../../theme/home-tokens.css"), "utf8")
	const names = [
		"--h-attn-work-bg",
		"--h-attn-work-fg",
		"--h-attn-overtime-bg",
		"--h-attn-overtime-fg",
		"--h-attn-anomaly-bg",
		"--h-attn-anomaly-fg",
		"--h-attn-rest-bg",
		"--h-attn-rest-fg",
		"--h-attn-holiday-bg",
		"--h-attn-holiday-fg",
	]
	for (const name of names) {
		const occurrences = tokens.split(name + ":").length - 1
		assert.equal(occurrences, 2, `${name} must be defined once for light and once for dark`)
	}
})

test("summary computes from cells rather than trusting a prop", () => {
	const source = read("AttendanceMonthSummary.vue")
	assert.match(source, /summarizeMonth/)
	assert.match(source, /computeProgress/)
})

// A month with no roster data has no denominator; showing "23 / 0" would be worse
// than showing nothing.
test("summary hides the progress bar when nothing is scheduled", () => {
	const source = read("AttendanceMonthSummary.vue")
	assert.match(source, /v-if="progress\.visible"/)
})

test("summary reuses the home progress track tokens", () => {
	const source = read("AttendanceMonthSummary.vue")
	assert.match(source, /--h-track-bg/)
	assert.match(source, /--h-track-fill-end/)
})

test("anomaly notice renders nothing when there is nothing to fix", () => {
	const source = read("AttendanceAnomalyNotice.vue")
	assert.match(source, /v-if="count > 0"/)
})

test("anomaly notice is an actionable labelled control", () => {
	const source = read("AttendanceAnomalyNotice.vue")
	assert.match(source, /<button/)
	assert.match(source, /aria-label/)
	assert.match(source, /emit\(["']open["']\)/)
	assert.match(source, /anomaly\.notice/)
})

function readCalendar() {
	return fs.readFileSync(path.resolve(currentDir, "../AttendanceCalendar.vue"), "utf8")
}

test("calendar drops its private theme machinery", () => {
	const source = readCalendar()
	assert.doesNotMatch(source, /THEME_SURFACE/)
	assert.doesNotMatch(source, /MutationObserver/)
	assert.doesNotMatch(source, /syncCalendarTheme/)
})

test("calendar drops the roster state and the dots", () => {
	const source = readCalendar()
	assert.doesNotMatch(source, /sale-event-dot|weekend-dot/)
	assert.doesNotMatch(source, /return "roster"/)
	assert.doesNotMatch(source, /cellBackground|isDarkHeatCell|heat_075|heat_125/)
})

test("calendar renders the extracted components", () => {
	const source = readCalendar()
	assert.match(source, /AttendanceDayCell/)
	assert.match(source, /AttendanceMonthSummary/)
	assert.match(source, /AttendanceAnomalyNotice/)
})

test("calendar uses the shared state and copy modules", () => {
	const source = readCalendar()
	assert.match(source, /deriveAttendanceState/)
	assert.match(source, /attendanceCalendarCopy/)
})

// The summary is the page's conclusion and belongs above the grid, not below it.
test("calendar puts the summary above the grid", () => {
	const source = readCalendar()
	const summaryAt = source.indexOf("AttendanceMonthSummary")
	const gridAt = source.indexOf("calendar-grid")
	assert.ok(summaryAt > -1 && gridAt > -1)
	assert.ok(summaryAt < gridAt, "summary must be rendered before the calendar grid")
})

// Every block already carries its own text — hours, 休, 祝, or the anomaly
// reason — so a legend explained nothing and cost the grid 4px of row height,
// which was the difference between a 16px number fitting its block or being
// clipped. Measured at 390x844 with the summary card and notice in place.
test("calendar has no legend row", () => {
	const source = readCalendar()
	assert.doesNotMatch(source, /class="legend"/)
	assert.doesNotMatch(source, /legendItems/)
	assert.doesNotMatch(source, /class="swatch"/)
})

test("roster data is still fetched for the progress denominator", () => {
	const source = readCalendar()
	assert.match(source, /get_my_schedule_calendar_data/)
	assert.match(source, /scheduledDays|scheduled-days/)
})

// A regex-driven refactor once deleted detailPillStyle while the dialog template
// still called it, which threw on click and unmounted the whole calendar. Nothing
// in the suite caught it, so this walks the template and demands a binding for
// every helper it invokes.
test("every function the calendar template calls is defined", () => {
	const source = readCalendar()
	const template = source.slice(0, source.indexOf("<script setup>"))
	const script = source.slice(source.indexOf("<script setup>"))

	const VUE_BUILTINS = new Set(["var", "t", "String", "Number", "Boolean", "Object", "Array"])
	const called = new Set(
		[...template.matchAll(/([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/g)]
			.map((m) => m[1])
			.filter((name) => !VUE_BUILTINS.has(name))
	)

	const missing = [...called].filter((name) => {
		const declared = new RegExp(
			`(function\\s+${name}\\b|const\\s+${name}\\s*=|let\\s+${name}\\s*=|import\\s[^\\n]*\\b${name}\\b)`
		)
		return !declared.test(script)
	})

	assert.deepEqual(missing, [], `template calls undefined: ${missing.join(", ")}`)
})
