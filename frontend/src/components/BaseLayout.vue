<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full">
				<div class="flex flex-col bg-white shadow-sm p-4">
					<div class="flex flex-row justify-between items-center">
						<div class="flex flex-row items-center gap-2 min-w-0">
							<button
								v-if="props.backRoute"
								@click="goBack"
								class="flex h-9 w-9 items-center justify-center rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-700"
							>
								<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
								</svg>
							</button>
							<img src="/uo-hr-logo.png" class="h-7 w-7 object-contain" alt="Logo" />
							<h2 class="text-xl font-bold text-gray-900 truncate">
								{{ props.pageTitle || __("UO HR") }}
							</h2>
						</div>
						<div class="flex flex-row items-center gap-2 ml-auto">
							<slot name="header-actions"></slot>
							<router-link
								:to="{ name: 'Notifications' }"
								v-slot="{ navigate }"
								class="flex flex-col items-center"
							>
								<span class="relative inline-block" @click="navigate">
									<FeatherIcon name="bell" class="h-6 w-6" />
									<span v-if="unreadNotificationsCount.data" class="notification-badge">
										{{ unreadNotificationsCount.data > 99 ? '99+' : unreadNotificationsCount.data }}
									</span>
								</span>
							</router-link>
							<router-link :to="{ name: 'Profile' }" class="flex flex-col items-center">
								<Avatar :image="user.data.user_image" :label="user.data.first_name" size="xl" />
							</router-link>
						</div>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding" :fullscreen="true">
			<div class="content-wrapper">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { inject } from "vue"
import { IonHeader, IonContent, IonPage } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"
import { useRouter } from "vue-router"

import { unreadNotificationsCount } from "@/data/notifications"

const user = inject("$user")
const __ = inject("$translate")
const router = useRouter()

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
	backRoute: {
		type: String,
		required: false,
		default: "",
	},
})

function goBack() {
	if (!props.backRoute) return
	router.replace(props.backRoute)
}
</script>

<style scoped>
.content-wrapper {
	display: flex;
	flex-direction: column;
	min-height: 100%;
	width: 100%;
	overflow-x: hidden;
}

.notification-badge {
	position: absolute;
	top: -6px;
	right: -6px;
	min-width: 18px;
	height: 18px;
	padding: 0 5px;
	font-size: 11px;
	font-weight: 600;
	line-height: 18px;
	text-align: center;
	color: white;
	background: #ef4444;
	border-radius: 9px;
	border: 2px solid white;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
</style>
