<template>
	<component :is="selectedAnimation" />
</template>

<script setup>
import { computed } from "vue"

import CheckInOfficeLightsAnimation from "@/components/home/success/CheckInOfficeLightsAnimation.vue"
import CheckInRunnerAnimation from "@/components/home/success/CheckInRunnerAnimation.vue"
import CheckInWorkLaunchAnimation from "@/components/home/success/CheckInWorkLaunchAnimation.vue"
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
	"office-lights": CheckInOfficeLightsAnimation,
	"work-launch": CheckInWorkLaunchAnimation,
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
