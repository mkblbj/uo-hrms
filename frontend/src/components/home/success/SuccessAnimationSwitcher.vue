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
import CheckOutCoffeeAnimation from "@/components/home/success/CheckOutCoffeeAnimation.vue"
import CheckOutCurvyBulldogAnimation from "@/components/home/success/CheckOutCurvyBulldogAnimation.vue"
import CheckOutKindSnailAnimation from "@/components/home/success/CheckOutKindSnailAnimation.vue"
import CheckOutTallFishAnimation from "@/components/home/success/CheckOutTallFishAnimation.vue"
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
}

const selectedAnimation = computed(() => {
	const fallbackId = props.variant === "checkout" ? "coffee" : "runner"
	return animationComponents[props.animationId] || animationComponents[fallbackId]
})
</script>
