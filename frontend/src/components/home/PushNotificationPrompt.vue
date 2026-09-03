<template>
	<section
		v-if="isVisible"
		class="push-notification-prompt"
		:class="`is-${promptState}`"
		aria-live="polite"
	>
		<div class="push-prompt-icon" aria-hidden="true">
			<FeatherIcon name="bell" class="h-5 w-5" />
		</div>
		<div class="push-prompt-content">
			<strong>{{ copy.title }}</strong>
			<p>{{ copy.message }}</p>
			<Button
				v-if="promptState === 'prompt'"
				variant="solid"
				theme="blue"
				class="push-prompt-button"
				:loading="isLoading"
				:disabled="isLoading"
				@click="enablePushNotifications"
			>
				{{ isLoading ? "設定中…" : "通知を有効にする" }}
			</Button>
			<p v-if="errorMessage" class="push-prompt-error" role="alert">
				{{ errorMessage }}
			</p>
		</div>
	</section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { Button, FeatherIcon, toast } from "frappe-ui"

import { resolvePushPromptState } from "@/utils/pushNotifications"

const promptState = ref("hidden")
const isLoading = ref(false)
const errorMessage = ref("")

const copy = computed(() => {
	if (promptState.value === "install") {
		return {
			title: "ホーム画面に追加してください",
			message: "シフト通知を利用するには、Safariの共有メニューからホーム画面に追加してください。",
		}
	}
	if (promptState.value === "denied") {
		return {
			title: "通知がオフになっています",
			message: "端末の設定からUO HRの通知を許可してください。",
		}
	}
	return {
		title: "シフト通知を有効にする",
		message: "勤務予定や変更を見逃さないよう、通知を有効にしてください。",
	}
})

const isVisible = computed(() => !["enabled", "hidden"].includes(promptState.value))

function isIosDevice() {
	return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
}

function isStandalone() {
	return Boolean(
		window.navigator.standalone || window.matchMedia?.("(display-mode: standalone)").matches
	)
}

function refreshPromptState() {
	if (!window.frappe?.boot?.push_relay_server_url) {
		promptState.value = "hidden"
		return
	}

	const client = window.frappePushNotification
	const hasNotificationApi = typeof window.Notification !== "undefined"
	const supported = Boolean(
		client && hasNotificationApi && "serviceWorker" in window.navigator && "PushManager" in window
	)
	promptState.value = resolvePushPromptState({
		isIos: isIosDevice(),
		isStandalone: isStandalone(),
		permission: hasNotificationApi ? window.Notification.permission : "default",
		hasToken: client?.isNotificationEnabled?.() || false,
		supported,
	})
}

async function enablePushNotifications() {
	const client = window.frappePushNotification
	if (!client || isLoading.value) return

	isLoading.value = true
	errorMessage.value = ""
	try {
		const result = await client.enableNotification()
		refreshPromptState()
		if (result?.permission_granted && promptState.value === "enabled") {
			toast({
				title: "通知を有効にしました",
				text: "シフト通知を受け取れます。",
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500",
			})
		} else if (promptState.value !== "denied") {
			errorMessage.value = "通知を有効にできませんでした。もう一度お試しください。"
		}
	} catch {
		refreshPromptState()
		errorMessage.value = "通知を有効にできませんでした。もう一度お試しください。"
	} finally {
		isLoading.value = false
	}
}

function onVisibilityChange() {
	if (document.visibilityState === "visible") refreshPromptState()
}

onMounted(() => {
	refreshPromptState()
	document.addEventListener("visibilitychange", onVisibilityChange)
})

onIonViewWillEnter(refreshPromptState)

onBeforeUnmount(() => {
	document.removeEventListener("visibilitychange", onVisibilityChange)
})
</script>

<style scoped>
.push-notification-prompt {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	width: 100%;
	padding: 16px;
	color: var(--h-fg-primary);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 16px;
}

.push-notification-prompt.is-denied {
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border-color: var(--h-summary-warn-bd);
}

.push-prompt-icon {
	display: grid;
	flex: 0 0 44px;
	width: 44px;
	height: 44px;
	place-items: center;
	color: var(--h-tab-active);
	background: var(--h-bg-card-inner);
	border-radius: 12px;
}

.is-denied .push-prompt-icon {
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border: 1px solid var(--h-summary-warn-bd);
}

.push-prompt-content {
	flex: 1;
	min-width: 0;
}

.push-prompt-content strong {
	display: block;
	font-size: 16px;
	line-height: 1.4;
	font-weight: 800;
}

.push-prompt-content p {
	margin: 4px 0 0;
	color: var(--h-fg-secondary);
	font-size: 14px;
	line-height: 1.5;
}

.is-denied .push-prompt-content p {
	color: var(--h-summary-warn-fg);
}

.push-prompt-button {
	min-height: 44px;
	margin-top: 12px;
	width: 100%;
}

.push-prompt-content .push-prompt-error {
	margin-top: 8px;
	color: var(--h-summary-warn-fg);
	font-size: 13px;
}
</style>
