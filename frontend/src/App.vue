<template>
	<ion-app>
		<ProfilePhotoGate
			v-if="photoGateActive"
			:key="session.user"
			:lang="language"
			@blocked="photoGateBlocked = $event"
		/>
		<template v-if="canUseApp">
			<ion-router-outlet id="main-content" />
			<InstallPrompt />
			<AppUpdatePrompt />
		</template>
		<ToastProvider />
	</ion-app>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue"
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
const photoGateBlocked = ref(true)
const photoGateActive = computed(
	() =>
		session.isLoggedIn &&
		employeeResource.data?.user_id === session.user &&
		!["Login", "ForgotPassword", "InvalidEmployee"].includes(route.name)
)
const canUseApp = computed(() => !photoGateActive.value || !photoGateBlocked.value)
const language = computed(() => resolveHomeLanguage(globalThis.window?.frappe?.boot))

// 每次进入员工应用或切换账号，都先等头像状态确认，避免先显示可操作的页面。
watch(
	[photoGateActive, () => session.user],
	() => {
		photoGateBlocked.value = true
	},
	{ flush: "sync" }
)

useTheme()

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
