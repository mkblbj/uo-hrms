<template>
	<ion-app>
		<ProfilePhotoGate v-if="photoGateActive" :key="session.user" :lang="language" />
		<ion-router-outlet id="main-content" />
		<ToastProvider />

		<InstallPrompt />
		<AppUpdatePrompt />
	</ion-app>
</template>

<script setup>
import { computed, onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"
import { useRoute } from "vue-router"

import { ToastProvider } from "frappe-ui"

import AppUpdatePrompt from "@/components/AppUpdatePrompt.vue"
import InstallPrompt from "@/components/InstallPrompt.vue"
import ProfilePhotoGate from "@/components/profile/ProfilePhotoGate.vue"
import { employeeResource } from "@/data/employee"
import { session } from "@/data/session"
import { showNotification } from "@/utils/pushNotifications"
import { useTheme } from "@/composables/useTheme"
import { resolveHomeLanguage } from "@/utils/homeExperience"

const route = useRoute()
// 登录后的员工页面都检查头像：没自己上传的弹出提醒（可以稍后再说，不挡页面）
const photoGateActive = computed(
	() =>
		session.isLoggedIn &&
		employeeResource.data?.user_id === session.user &&
		!["Login", "ForgotPassword", "InvalidEmployee"].includes(route.name)
)
const language = computed(() => resolveHomeLanguage(globalThis.window?.frappe?.boot))

useTheme()

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
