import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
function readComponentSource(fileName) {
	try {
		return readFileSync(path.join(currentDir, "success", fileName), "utf8")
	} catch {
		return ""
	}
}

const runnerSource = readComponentSource("CheckInRunnerAnimation.vue")
const blackRabbitSource = readComponentSource("CheckInBlackRabbitAnimation.vue")
const popularOwlSource = readComponentSource("CheckInPopularOwlAnimation.vue")
const emptySnailSource = readComponentSource("CheckInEmptySnailAnimation.vue")
const monaLisaSource = readComponentSource("CheckInMonaLisaAnimation.vue")
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
const sweetJellyfishSource = readComponentSource("CheckOutSweetJellyfishAnimation.vue")
const chattyZebraSource = readComponentSource("CheckOutChattyZebraAnimation.vue")
const neatTigerSource = readComponentSource("CheckOutNeatTigerAnimation.vue")
const foolishRabbitSource = readComponentSource("CheckOutFoolishRabbitAnimation.vue")
const stalePandaSource = readComponentSource("CheckOutStalePandaAnimation.vue")
const nastyVampirebatSource = readComponentSource("CheckOutNastyVampirebatAnimation.vue")
const happyDogSource = readComponentSource("CheckOutHappyDogAnimation.vue")
const luckyEmuSource = readComponentSource("CheckOutLuckyEmuAnimation.vue")
const tenderBaboonSource = readComponentSource("CheckOutTenderBaboonAnimation.vue")
const wetGooseSource = readComponentSource("CheckOutWetGooseAnimation.vue")
const lightTermiteSource = readComponentSource("CheckOutLightTermiteAnimation.vue")
const tidySkunkSource = readComponentSource("CheckOutTidySkunkAnimation.vue")
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

test("check-in animation pool maps the requested uiverse source variants", () => {
	assert.match(blackRabbitSource, /uiverse\.io\/JohnnyCSilva\/black-rabbit-68/)
	assert.match(blackRabbitSource, /class="coin"/)
	assert.match(blackRabbitSource, /class="svg_back"/)
	assert.match(blackRabbitSource, /@keyframes rotate_4001510/)
	assert.match(blackRabbitSource, /fill="#F7931A"/)

	assert.match(popularOwlSource, /uiverse\.io\/vinodjangid07\/popular-owl-27/)
	assert.match(popularOwlSource, /class="truckWrapper"/)
	assert.match(popularOwlSource, /class="truckBody"/)
	assert.match(popularOwlSource, /@keyframes roadAnimation/)
	assert.match(popularOwlSource, /class="lampPost"/)

	assert.match(emptySnailSource, /uiverse\.io\/Nawsome\/empty-snail-69/)
	assert.match(emptySnailSource, /class="switch switch--auto-on"/)
	assert.match(emptySnailSource, /\.switch input:checked \+ \.button/)
	assert.match(emptySnailSource, /@keyframes empty-snail-auto-on/)
	assert.match(emptySnailSource, /@keyframes flicker/)

	assert.match(monaLisaSource, /Uiverse\.io by SelfMadeSystem/)
	assert.match(monaLisaSource, /class="loader"/)
	assert.match(monaLisaSource, /pathLength="360"/)
	assert.match(monaLisaSource, /@keyframes dashArray/)
	assert.match(monaLisaSource, /@keyframes dashOffset/)

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

	assert.match(sweetJellyfishSource, /uiverse\.io\/vinodjangid07\/sweet-jellyfish-62/)
	assert.match(sweetJellyfishSource, /class="catContainer"/)
	assert.match(sweetJellyfishSource, /class="bigzzz"/)

	assert.match(chattyZebraSource, /uiverse\.io\/StealthWorm\/chatty-zebra-11/)
	assert.match(chattyZebraSource, /class="carousel"/)
	assert.match(chattyZebraSource, /class="robots"/)

	assert.match(neatTigerSource, /uiverse\.io\/alexruix\/neat-tiger-82/)
	assert.match(neatTigerSource, /class="box1"/)
	assert.match(neatTigerSource, /@keyframes abox3/)

	assert.match(foolishRabbitSource, /uiverse\.io\/whoisyourdeadie\/foolish-rabbit-13/)
	assert.match(foolishRabbitSource, /class="matrix-container"/)
	assert.match(foolishRabbitSource, /@keyframes fall/)

	assert.match(stalePandaSource, /uiverse\.io\/Shoh2008\/stale-panda-35/)
	assert.match(stalePandaSource, /@keyframes bike/)

	assert.match(nastyVampirebatSource, /uiverse\.io\/TheAbieza\/nasty-vampirebat-71/)
	assert.match(nastyVampirebatSource, /class="plate"/)
	assert.match(nastyVampirebatSource, /@keyframes rotation/)

	assert.match(happyDogSource, /uiverse\.io\/csemszepp\/happy-dog-58/)
	assert.match(happyDogSource, /class="vader"/)
	assert.match(happyDogSource, /class="sword animation-left"/)

	assert.match(luckyEmuSource, /uiverse\.io\/Shoh2008\/lucky-emu-65/)
	assert.match(luckyEmuSource, /@keyframes faceLift/)

	assert.match(tenderBaboonSource, /uiverse\.io\/Subaashbala\/tender-baboon-47/)
	assert.match(tenderBaboonSource, /id="bird"/)
	assert.match(tenderBaboonSource, /@keyframes flap/)

	assert.match(wetGooseSource, /uiverse\.io\/vikas7754\/wet-goose-61/)
	assert.match(wetGooseSource, /class="truck"/)
	assert.match(wetGooseSource, /class="truck__headlight"/)

	assert.match(lightTermiteSource, /uiverse\.io\/Lakshay-art\/light-termite-47/)
	assert.match(lightTermiteSource, /class="face"/)
	assert.match(lightTermiteSource, /class="smileL"/)

	assert.match(tidySkunkSource, /uiverse\.io\/JkHuger\/tidy-skunk-55/)
	assert.match(tidySkunkSource, /class="dots2"/)
	assert.match(tidySkunkSource, /@keyframes chomp2/)
})

test("success animation switcher maps every configured animation id", () => {
	for (const animationId of [
		"runner",
		"black-rabbit-68",
		"popular-owl-27",
		"empty-snail-69",
		"mona-lisa",
		"coffee",
		"curvy-bulldog-27",
		"wet-mayfly-23",
		"kind-snail-5",
		"tall-fish-38",
		"sweet-jellyfish-62",
		"chatty-zebra-11",
		"neat-tiger-82",
		"foolish-rabbit-13",
		"stale-panda-35",
		"nasty-vampirebat-71",
		"happy-dog-58",
		"lucky-emu-65",
		"tender-baboon-47",
		"wet-goose-61",
		"light-termite-47",
		"tidy-skunk-55",
	]) {
		assert.match(switcherSource, new RegExp(`"${animationId}"`))
	}
})
