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
