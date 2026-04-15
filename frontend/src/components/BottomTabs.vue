<template>
	<ion-tab-bar
		slot="bottom"
		class="bg-white shadow-md sm:w-96 py-2 pb-2 standalone:pb-safe-bottom"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.key"
			:tab="item.key"
			:href="item.route"
			:class="[
				'bg-white text-xs space-y-1.5 border-t-2 transition active:scale-95',
				isActive(item)
					? 'border-blue-600 text-blue-700 font-semibold'
					: 'border-transparent text-gray-500 font-normal hover:text-gray-700',
			]"
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
