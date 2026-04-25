import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const runnerSource = readFileSync(path.join(currentDir, "success", "CheckInRunnerAnimation.vue"), "utf8")
const coffeeSource = readFileSync(path.join(currentDir, "success", "CheckOutCoffeeAnimation.vue"), "utf8")

test("runner animation keeps the original speeding markup and clouds", () => {
	assert.match(runnerSource, /<div class="clouds">/)
	assert.match(runnerSource, /<div class="cloud cloud1"><\/div>/)
	assert.match(runnerSource, /\.loader\s*\{[\s\S]*animation:\s*speeder 0\.4s linear infinite/i)
	assert.match(runnerSource, /\.longfazers span\s*\{[\s\S]*background:\s*#ffffff/i)
	assert.match(runnerSource, /@keyframes moveClouds/i)
})

test("coffee animation keeps the original machine markup and delayed liquid cycle", () => {
	assert.match(coffeeSource, /coffee-header__button-one/)
	assert.match(coffeeSource, /coffee-medium__smoke-one/)
	assert.match(coffeeSource, /\.coffee-medium__liquid\s*\{[\s\S]*animation:\s*liquid 4s 4s linear infinite/i)
	assert.match(coffeeSource, /@keyframes smokeOne/i)
	assert.match(coffeeSource, /@keyframes smokeTwo/i)
})
