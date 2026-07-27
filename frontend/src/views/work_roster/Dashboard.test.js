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
