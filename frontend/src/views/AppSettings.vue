<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen">
				<div class="w-full sm:w-96">
					<header
						class="flex flex-row bg-white shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
					>
						<div class="flex flex-row items-center">
							<Button variant="ghost" class="!pl-0 hover:bg-white" @click="router.back()">
								<Icon icon="lucide-chevron-left" class="h-5 w-5" />
							</Button>
							<h2 class="text-2xl-semibold text-gray-900">{{ __("Settings") }}</h2>
						</div>
					</header>

					<div class="flex flex-col gap-5 my-4 w-full p-4">
						<LanguagePreferenceCard />
						<div class="flex flex-col bg-white rounded-4">
							<div
								class="flex flex-row cursor-pointer flex-start p-4 items-center justify-between border-b"
							>
								<router-link
									:to="{ name: 'ChangePassword' }"
									class="flex flex-row items-center justify-between w-full"
								>
									<div class="flex flex-row items-center gap-3 grow">
										<Icon icon="lucide-lock" class="h-5 w-5 text-gray-500" />
										<div class="text-base text-gray-800">
											{{ __("Change Password") }}
										</div>
									</div>
									<Icon icon="lucide-chevron-right" class="h-5 w-5 text-gray-500" />
								</router-link>
							</div>
						</div>

						<div class="flex flex-col bg-white rounded-4">
							<Switch
								size="md"
								:label="__('Enable Push Notifications')"
								:class="description ? 'p-2' : ''"
								:model-value="pushNotificationState"
								:disabled="disablePushSetting"
								:description="description"
								@update:model-value="togglePushNotifications"
							/>
						</div>
						<div v-if="isLoading" class="flex -mt-2 items-center justify-center gap-2">
							<LoadingIndicator class="w-3 h-3 text-gray-800" />
							<span class="text-gray-900 text-sm">
								{{
									pushNotificationState
										? __("Disabling Push Notifications...")
										: __("Enabling Push Notifications...")
								}}
							</span>
						</div>
						<PasskeyManager />
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { computed, inject, ref } from "vue"
import { IonPage, IonContent, onIonViewWillEnter } from "@ionic/vue"
import { useRouter } from "vue-router"
import { Icon, Switch, toast, LoadingIndicator, Button } from "frappe-ui"

import LanguagePreferenceCard from "@/components/settings/LanguagePreferenceCard.vue"
import PasskeyManager from "@/components/PasskeyManager.vue"
import { arePushNotificationsEnabled } from "@/data/notifications"

const __ = inject("$translate")
const router = useRouter()

const pushNotificationState = ref(window.frappePushNotification?.isNotificationEnabled())
const isLoading = ref(false)

onIonViewWillEnter(() => {
	pushNotificationState.value = window.frappePushNotification?.isNotificationEnabled()
})

const disablePushSetting = computed(() => {
	return (
		!(window.frappe?.boot.push_relay_server_url && arePushNotificationsEnabled.data) ||
		isLoading.value
	)
})

const description = computed(() => {
	return !(window.frappe?.boot.push_relay_server_url && arePushNotificationsEnabled.data)
		? __("Push notifications have been disabled on your site")
		: ""
})

const togglePushNotifications = (newValue) => {
	if (newValue) {
		enablePushNotifications()
	} else {
		isLoading.value = true
		window.frappePushNotification
			.disableNotification()
			.then(() => {
				pushNotificationState.value = false
				toast.success(__("Success"), {
					description: __("Push notifications disabled"),
				})
			})
			.catch((error) => {
				toast.error(__("Error"), {
					description: __(error.message),
				})
			})
			.finally(() => {
				isLoading.value = false
			})
	}
}
const enablePushNotifications = () => {
	isLoading.value = true

	window.frappePushNotification
		.enableNotification()
		.then((data) => {
			if (data.permission_granted) {
				pushNotificationState.value = true
			} else {
				toast.error(__("Error"), {
					description: __("Push Notification permission denied"),
				})
				pushNotificationState.value = false
			}
		})
		.catch((error) => {
			toast.error(__("Error"), {
				description: __(error.message),
			})
			pushNotificationState.value = false
		})
		.finally(() => {
			isLoading.value = false
		})
}
</script>
