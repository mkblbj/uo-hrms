import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const runnerSource = readFileSync(path.join(currentDir, "success", "CheckInRunnerAnimation.vue"), "utf8")
const officeLightsSource = readFileSync(
	path.join(currentDir, "success", "CheckInOfficeLightsAnimation.vue"),
	"utf8"
)
const workLaunchSource = readFileSync(
	path.join(currentDir, "success", "CheckInWorkLaunchAnimation.vue"),
	"utf8"
)
const coffeeSource = readFileSync(path.join(currentDir, "success", "CheckOutCoffeeAnimation.vue"), "utf8")
const curvyBulldogSource = readFileSync(
	path.join(currentDir, "success", "CheckOutCurvyBulldogAnimation.vue"),
	"utf8"
)
const wetMayflySource = readFileSync(
	path.join(currentDir, "success", "CheckOutWetMayflyAnimation.vue"),
	"utf8"
)
const kindSnailSource = readFileSync(
	path.join(currentDir, "success", "CheckOutKindSnailAnimation.vue"),
	"utf8"
)
const tallFishSource = readFileSync(
	path.join(currentDir, "success", "CheckOutTallFishAnimation.vue"),
	"utf8"
)
const switcherSource = readFileSync(
	path.join(currentDir, "success", "SuccessAnimationSwitcher.vue"),
	"utf8"
)

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

test("check-in animation pool includes office lights and work launch variants", () => {
	assert.match(officeLightsSource, /office-lights-shell/)
	assert.match(officeLightsSource, /office-window/)
	assert.match(officeLightsSource, /@keyframes office-light-on/i)

	assert.match(workLaunchSource, /work-launch-shell/)
	assert.match(workLaunchSource, /work-launch-bar__fill/)
	assert.match(workLaunchSource, /@keyframes work-launch-fill/i)
})

test("check-out animation pool includes the requested uiverse variants", () => {
	assert.match(curvyBulldogSource, /uiverse\.io\/Shoh2008\/curvy-bulldog-27/)
	assert.match(curvyBulldogSource, /curvy-bulldog-shell/)
	assert.match(wetMayflySource, /uiverse\.io\/Nawsome\/wet-mayfly-23/)
	assert.match(wetMayflySource, /wet-mayfly-shell/)
	assert.match(kindSnailSource, /uiverse\.io\/Novaxlo\/kind-snail-5/)
	assert.match(kindSnailSource, /kind-snail-shell/)
	assert.match(tallFishSource, /uiverse\.io\/Pradeepsaranbishnoi\/tall-fish-38/)
	assert.match(tallFishSource, /tall-fish-shell/)
})

test("success animation switcher maps every configured animation id", () => {
	for (const animationId of [
		"runner",
		"office-lights",
		"work-launch",
		"coffee",
		"curvy-bulldog-27",
		"wet-mayfly-23",
		"kind-snail-5",
		"tall-fish-38",
	]) {
		assert.match(switcherSource, new RegExp(`"${animationId}"`))
	}
})
