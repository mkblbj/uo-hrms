<template>
	<ion-tab-bar
		slot="bottom"
		class="shadow-sm sm:w-96 py-1.5 pb-2 standalone:pb-safe-bottom" style="background: var(--h-tab-bg); border-top: 1px solid var(--h-tab-bd)"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.key"
			:tab="item.key"
			:href="item.route"
			:class="[
				'bg-transparent text-xs space-y-1.5 border-t-2 transition active:scale-95',
				isActive(item)
					? 'font-semibold'
					: 'border-transparent font-normal',
			]"
			:style="isActive(item) ? { borderColor: 'var(--h-tab-active)', color: 'var(--h-tab-active)' } : { color: 'var(--h-tab-inactive)' }"
		>
			<component :is="item.icon" class="h-5 w-5" />
			<div>{{ item.title }}</div>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { computed } from "vue"
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import HomeIcon from "@/components/icons/HomeIcon.vue"
import RosterIcon from "@/components/icons/RosterIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import { getBottomTabItems } from "@/utils/homeExperience"

const route = useRoute()
const lang = computed(() => window.frappe?.boot?.lang || "zh")
const iconByKey = {
	home: HomeIcon,
	attendance: AttendanceIcon,
	roster: RosterIcon,
	expenses: ExpenseIcon,
	salary: SalaryIcon,
}
const tabItems = computed(() =>
	getBottomTabItems(lang.value).map((item) => ({ ...item, icon: iconByKey[item.key] })),
)

function isActive(item) {
	return route.path === item.route
}
</script>

<style scoped>
ion-tab-button {
	--color: var(--h-tab-inactive);
	--color-selected: var(--h-tab-active);
	background: transparent;
}
</style>
