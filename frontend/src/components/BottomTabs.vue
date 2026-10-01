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
			:aria-label="item.key === 'chat' ? chatUnread.label : item.title"
			:class="[
				'bg-transparent text-xs space-y-1.5 border-t-2 transition active:scale-95',
				isActive(item)
					? 'font-semibold'
					: 'border-transparent font-normal',
			]"
			:style="isActive(item) ? { borderColor: 'var(--h-tab-active)', color: 'var(--h-tab-active)' } : { color: 'var(--h-tab-inactive)' }"
		>
			<span class="relative inline-flex">
				<component :is="item.icon" class="h-5 w-5" />
				<span v-if="item.key === 'chat' && chatUnread.count" class="chat-unread-badge" aria-hidden="true">{{ chatUnread.text }}</span>
			</span>
			<div>{{ item.title }}</div>
		</ion-tab-button>
		<span class="sr-only" role="status" aria-atomic="true">{{ chatUnread.count ? chatUnread.label : '' }}</span>
	</ion-tab-bar>
</template>

<script setup>
import { computed, inject } from "vue"
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ChatIcon from "@/components/icons/ChatIcon.vue"
import ExpenseIcon from "@/components/icons/ExpenseIcon.vue"
import HomeIcon from "@/components/icons/HomeIcon.vue"
import RosterIcon from "@/components/icons/RosterIcon.vue"
import SalaryIcon from "@/components/icons/SalaryIcon.vue"
import { getBottomTabItems } from "@/utils/homeExperience"
import { useChatUnread } from "@/composables/useChatUnread"

const route = useRoute()
const user = inject("$user")
const socket = inject("$socket")
const lang = computed(() => window.frappe?.boot?.lang || "zh")
const chatEnabled = computed(
	() => Boolean(window.frappe?.boot?.raven_installed) && Boolean(user.data?.roles?.includes("Raven User")),
)
const chatUnread = useChatUnread(socket, chatEnabled, user, lang)
const iconByKey = {
	home: HomeIcon,
	attendance: AttendanceIcon,
	roster: RosterIcon,
	chat: ChatIcon,
	expenses: ExpenseIcon,
	salary: SalaryIcon,
}
const tabItems = computed(() =>
	getBottomTabItems(lang.value, { chatEnabled: chatEnabled.value }).map((item) => ({ ...item, icon: iconByKey[item.key] })),
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
/* Ionic clips a tab button's contents to the button box. The unread badge sits
   above the icon's top-right corner and pokes over that edge, which cut its top
   flat. The clip only keeps Material mode's tap ripple inside the button; the app
   runs Ionic's iOS mode everywhere, so nothing relies on it. */
ion-tab-button::part(native) {
	overflow: visible;
}
.chat-unread-badge {
	position: absolute;
	top: -7px;
	left: 12px;
	min-width: 18px;
	height: 18px;
	padding: 0 4px;
	border-radius: 9px;
	background: var(--h-badge-bg, #ef4444);
	color: white;
	border: 1px solid var(--h-badge-bd, white);
	font-size: 10px;
	font-weight: 600;
	line-height: 16px;
	text-align: center;
}
</style>
