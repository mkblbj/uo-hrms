import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const runnerSource = readFileSync(path.join(currentDir, "success", "CheckInRunnerAnimation.vue"), "utf8")
const coffeeSource = readFileSync(path.join(currentDir, "success", "CheckOutCoffeeAnimation.vue"), "utf8")

test("runner animation starts from the shell instead of relying only on subtle inner motion", () => {
	assert.match(runnerSource, /\.runner-shell\s*\{[\s\S]*animation:\s*runner-bob/i)
})

test("coffee animation does not wait multiple seconds before showing motion", () => {
	assert.doesNotMatch(coffeeSource, /3500ms|[\s:(][4-7]s\b/)
	assert.match(coffeeSource, /\.coffee-shell\s*\{[\s\S]*animation:\s*coffee-float/i)
})
