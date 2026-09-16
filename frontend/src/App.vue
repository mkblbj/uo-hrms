<template>
	<ion-app>
		<ion-router-outlet id="main-content" />
		<ToastProvider />

		<InstallPrompt />
		<AppUpdatePrompt />
	</ion-app>
</template>

<script setup>
import { onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { ToastProvider } from "frappe-ui"

import AppUpdatePrompt from "@/components/AppUpdatePrompt.vue"
import InstallPrompt from "@/components/InstallPrompt.vue"
import { showNotification } from "@/utils/pushNotifications"
import { useTheme } from "@/composables/useTheme"

useTheme()

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
