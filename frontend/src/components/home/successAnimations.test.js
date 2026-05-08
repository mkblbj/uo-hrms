import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const runnerSource = readFileSync(path.join(currentDir, "success", "CheckInRunnerAnimation.vue"), "utf8")
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

test("check-in animation pool only maps the runner variant", () => {
	assert.doesNotMatch(switcherSource, /office-lights/)
	assert.doesNotMatch(switcherSource, /work-launch/)
})

test("check-out animation pool keeps the requested uiverse source variants", () => {
	assert.match(curvyBulldogSource, /uiverse\.io\/Shoh2008\/curvy-bulldog-27/)
	assert.match(curvyBulldogSource, /class="loader"/)
	assert.match(curvyBulldogSource, /background-image:\s*linear-gradient\(#ddd 50%, #bbb 51%\)/)
	assert.match(curvyBulldogSource, /@keyframes spin/)
	assert.match(curvyBulldogSource, /@keyframes shake/)

	assert.match(wetMayflySource, /uiverse\.io\/Nawsome\/wet-mayfly-23/)
	assert.match(wetMayflySource, /class="wheel-and-hamster"/)
	assert.match(wetMayflySource, /class="hamster__limb hamster__limb--fr"/)
	assert.match(wetMayflySource, /@keyframes hamsterFRLimb/)
	assert.match(wetMayflySource, /@keyframes spoke/)

	assert.match(kindSnailSource, /uiverse\.io\/Novaxlo\/kind-snail-5/)
	assert.match(kindSnailSource, /class="capybaraloader"/)
	assert.match(kindSnailSource, /class="capyhead"/)
	assert.match(kindSnailSource, /@keyframes moveleg2/)
	assert.match(kindSnailSource, /@keyframes moveline/)

	assert.match(tallFishSource, /uiverse\.io\/Pradeepsaranbishnoi\/tall-fish-38/)
	assert.match(tallFishSource, /class="🤚"/)
	assert.match(tallFishSource, /class="👉"/)
	assert.match(tallFishSource, /@keyframes tap-upper-4/)
})

test("success animation switcher maps every configured animation id", () => {
	for (const animationId of [
		"runner",
		"coffee",
		"curvy-bulldog-27",
		"wet-mayfly-23",
		"kind-snail-5",
		"tall-fish-38",
	]) {
		assert.match(switcherSource, new RegExp(`"${animationId}"`))
	}
})
