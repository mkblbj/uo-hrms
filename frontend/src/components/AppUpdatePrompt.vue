<template>
	<div v-if="showPrompt" class="app-update-prompt" role="status" aria-live="polite">
		<div class="app-update-copy">
			<div class="app-update-title">{{ copy.title }}</div>
			<div class="app-update-message">{{ copy.message }}</div>
		</div>
		<button class="app-update-action" type="button" @click="reloadApp">
			{{ copy.action }}
		</button>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import {
	FRONTEND_VERSION_CHECK_INTERVAL_MS,
	createFrontendVersionChecker,
	requestServiceWorkerUpdate,
} from "@/utils/frontendVersion"
import { resolveHomeLanguage } from "@/utils/homeExperience"

const COPY = {
	zh: {
		title: "新版本可用",
		message: "刷新后载入最新界面",
		action: "刷新",
	},
	ja: {
		title: "新しいバージョンがあります",
		message: "更新すると最新画面を読み込みます",
		action: "更新",
	},
	en: {
		title: "Update available",
		message: "Refresh to load the latest app",
		action: "Refresh",
	},
}

const checker = createFrontendVersionChecker()
const checking = ref(false)
const showPrompt = ref(false)
const language = computed(() => resolveHomeLanguage(globalThis.window?.frappe?.boot))
const copy = computed(() => COPY[language.value] || COPY.zh)

let intervalId = null

async function checkForUpdate() {
	if (checking.value || showPrompt.value) return

	checking.value = true
	try {
		await requestServiceWorkerUpdate()
		const result = await checker.check()
		showPrompt.value = result.updateAvailable
	} finally {
		checking.value = false
	}
}

function handleVisibilityChange() {
	if (document.visibilityState === "visible") {
		checkForUpdate()
	}
}

function reloadApp() {
	window.location.reload()
}

onMounted(() => {
	checkForUpdate()

	window.addEventListener("focus", checkForUpdate)
	window.addEventListener("online", checkForUpdate)
	document.addEventListener("visibilitychange", handleVisibilityChange)
	intervalId = window.setInterval(checkForUpdate, FRONTEND_VERSION_CHECK_INTERVAL_MS)
})

onBeforeUnmount(() => {
	window.removeEventListener("focus", checkForUpdate)
	window.removeEventListener("online", checkForUpdate)
	document.removeEventListener("visibilitychange", handleVisibilityChange)

	if (intervalId) {
		window.clearInterval(intervalId)
	}
})
</script>

<style scoped>
.app-update-prompt {
	position: fixed;
	z-index: 10000;
	left: max(16px, env(safe-area-inset-left));
	right: max(16px, env(safe-area-inset-right));
	bottom: calc(82px + env(safe-area-inset-bottom));
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	max-width: 420px;
	margin: 0 auto;
	padding: 12px 12px 12px 14px;
	border: 1px solid rgba(148, 163, 184, 0.22);
	border-radius: 16px;
	background: rgba(255, 255, 255, 0.98);
	box-shadow: 0 18px 36px rgba(15, 23, 42, 0.18);
}

.app-update-copy {
	min-width: 0;
}

.app-update-title {
	color: #0f172a;
	font-size: 14px;
	font-weight: 700;
	line-height: 1.35;
}

.app-update-message {
	margin-top: 2px;
	color: #64748b;
	font-size: 12px;
	line-height: 1.35;
}

.app-update-action {
	flex: 0 0 auto;
	min-height: 36px;
	padding: 0 14px;
	border: 0;
	border-radius: 10px;
	background: #2563eb;
	color: #fff;
	font-size: 14px;
	font-weight: 700;
	line-height: 1;
}

.app-update-action:active {
	transform: translateY(1px);
}

@media (min-width: 768px) {
	.app-update-prompt {
		left: auto;
		right: 24px;
		bottom: 24px;
		width: min(420px, calc(100vw - 48px));
	}
}
</style>
