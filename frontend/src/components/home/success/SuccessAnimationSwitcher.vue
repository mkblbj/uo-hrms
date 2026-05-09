<template>
	<component :is="selectedAnimation" />
</template>

<script setup>
import { computed } from "vue"

import CheckInBlackRabbitAnimation from "@/components/home/success/CheckInBlackRabbitAnimation.vue"
import CheckInEmptySnailAnimation from "@/components/home/success/CheckInEmptySnailAnimation.vue"
import CheckInMonaLisaAnimation from "@/components/home/success/CheckInMonaLisaAnimation.vue"
import CheckInPopularOwlAnimation from "@/components/home/success/CheckInPopularOwlAnimation.vue"
import CheckInRunnerAnimation from "@/components/home/success/CheckInRunnerAnimation.vue"
import CheckOutChattyZebraAnimation from "@/components/home/success/CheckOutChattyZebraAnimation.vue"
import CheckOutCoffeeAnimation from "@/components/home/success/CheckOutCoffeeAnimation.vue"
import CheckOutCurvyBulldogAnimation from "@/components/home/success/CheckOutCurvyBulldogAnimation.vue"
import CheckOutFoolishRabbitAnimation from "@/components/home/success/CheckOutFoolishRabbitAnimation.vue"
import CheckOutHappyDogAnimation from "@/components/home/success/CheckOutHappyDogAnimation.vue"
import CheckOutKindSnailAnimation from "@/components/home/success/CheckOutKindSnailAnimation.vue"
import CheckOutLightTermiteAnimation from "@/components/home/success/CheckOutLightTermiteAnimation.vue"
import CheckOutLuckyEmuAnimation from "@/components/home/success/CheckOutLuckyEmuAnimation.vue"
import CheckOutNastyVampirebatAnimation from "@/components/home/success/CheckOutNastyVampirebatAnimation.vue"
import CheckOutNeatTigerAnimation from "@/components/home/success/CheckOutNeatTigerAnimation.vue"
import CheckOutStalePandaAnimation from "@/components/home/success/CheckOutStalePandaAnimation.vue"
import CheckOutSweetJellyfishAnimation from "@/components/home/success/CheckOutSweetJellyfishAnimation.vue"
import CheckOutTallFishAnimation from "@/components/home/success/CheckOutTallFishAnimation.vue"
import CheckOutTenderBaboonAnimation from "@/components/home/success/CheckOutTenderBaboonAnimation.vue"
import CheckOutTidySkunkAnimation from "@/components/home/success/CheckOutTidySkunkAnimation.vue"
import CheckOutWetGooseAnimation from "@/components/home/success/CheckOutWetGooseAnimation.vue"
import CheckOutWetMayflyAnimation from "@/components/home/success/CheckOutWetMayflyAnimation.vue"

const props = defineProps({
	variant: {
		type: String,
		required: true,
	},
	animationId: {
		type: String,
		default: "",
	},
})

const animationComponents = {
	runner: CheckInRunnerAnimation,
	"black-rabbit-68": CheckInBlackRabbitAnimation,
	"popular-owl-27": CheckInPopularOwlAnimation,
	"empty-snail-69": CheckInEmptySnailAnimation,
	"mona-lisa": CheckInMonaLisaAnimation,
	coffee: CheckOutCoffeeAnimation,
	"curvy-bulldog-27": CheckOutCurvyBulldogAnimation,
	"wet-mayfly-23": CheckOutWetMayflyAnimation,
	"kind-snail-5": CheckOutKindSnailAnimation,
	"tall-fish-38": CheckOutTallFishAnimation,
	"sweet-jellyfish-62": CheckOutSweetJellyfishAnimation,
	"chatty-zebra-11": CheckOutChattyZebraAnimation,
	"neat-tiger-82": CheckOutNeatTigerAnimation,
	"foolish-rabbit-13": CheckOutFoolishRabbitAnimation,
	"stale-panda-35": CheckOutStalePandaAnimation,
	"nasty-vampirebat-71": CheckOutNastyVampirebatAnimation,
	"happy-dog-58": CheckOutHappyDogAnimation,
	"lucky-emu-65": CheckOutLuckyEmuAnimation,
	"tender-baboon-47": CheckOutTenderBaboonAnimation,
	"wet-goose-61": CheckOutWetGooseAnimation,
	"light-termite-47": CheckOutLightTermiteAnimation,
	"tidy-skunk-55": CheckOutTidySkunkAnimation,
}

const selectedAnimation = computed(() => {
	const fallbackId = props.variant === "checkout" ? "coffee" : "runner"
	return animationComponents[props.animationId] || animationComponents[fallbackId]
})
</script>
