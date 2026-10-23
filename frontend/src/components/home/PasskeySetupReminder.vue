<template>
	<section v-if="showCard" class="passkey-setup-prompt" aria-live="polite">
		<div class="passkey-setup-icon" aria-hidden="true">
			<Icon icon="lucide-scan-face" class="h-5 w-5" />
		</div>
		<div class="passkey-setup-content">
			<strong>{{ copy.title }}</strong>
			<p>{{ copy.message }}</p>
			<button
				type="button"
				class="passkey-setup-button"
				:aria-expanded="sheetOpen"
				@click="sheetOpen = true"
			>
				{{ copy.action }}
			</button>
		</div>
	</section>

	<IonModal
		:is-open="sheetOpen"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
		class="passkey-setup-modal"
		@didDismiss="sheetOpen = false"
	>
		<div class="passkey-setup-sheet">
			<div class="passkey-setup-heading">
				<h2>{{ copy.title }}</h2>
				<button type="button" :aria-label="copy.close" @click="sheetOpen = false">
					<Icon icon="lucide-x" class="h-5 w-5" aria-hidden="true" />
				</button>
			</div>
			<PasskeyManager v-if="sheetOpen" @registered="onRegistered" />
		</div>
	</IonModal>
</template>

<script setup>
import { computed, ref } from "vue"
import { IonModal } from "@ionic/vue"
import { Icon } from "frappe-ui"

import PasskeyManager from "@/components/PasskeyManager.vue"

const props = defineProps({
	context: { type: Object, default: null },
	platformSupported: { type: Boolean, default: false },
	lang: { type: String, default: "zh" },
})
const emit = defineEmits(["registered"])
const sheetOpen = ref(false)

// 先让员工完成设置，是否开放新打卡方式仍由 HR 设置决定。
const showCard = computed(() => props.platformSupported && props.context?.has_passkey === false)
const copy = computed(() => {
	const labels = {
		zh: {
			title: "设置面容／指纹打卡",
			message: "打卡方式升级，请先完成设置。",
			action: "去设置",
			close: "关闭",
		},
		ja: {
			title: "顔認証・指紋認証の打刻を設定",
			message: "新しい打刻方法を使うため、先に設定してください。",
			action: "設定する",
			close: "閉じる",
		},
		en: {
			title: "Set up face / fingerprint check-in",
			message: "Set up your phone for the new check-in method.",
			action: "Set Up",
			close: "Close",
		},
	}
	return labels[props.lang] || labels.zh
})

function onRegistered() {
	sheetOpen.value = false
	emit("registered")
}
</script>

<style scoped>
.passkey-setup-prompt {
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

.passkey-setup-icon {
	display: grid;
	flex: 0 0 44px;
	width: 44px;
	height: 44px;
	place-items: center;
	color: var(--h-tab-active);
	background: var(--h-bg-card-inner);
	border-radius: 12px;
}

.passkey-setup-content {
	flex: 1;
	min-width: 0;
}

.passkey-setup-content strong {
	display: block;
	font-size: 16px;
	font-weight: 800;
	line-height: 1.4;
}

.passkey-setup-content p {
	margin: 4px 0 0;
	color: var(--h-fg-secondary);
	font-size: 14px;
	line-height: 1.5;
}

.passkey-setup-button {
	width: 100%;
	min-height: 44px;
	margin-top: 12px;
	border-radius: 12px;
	color: var(--h-scan-fg);
	background: var(--h-scan-bg);
	font-size: 15px;
	font-weight: 800;
}

.passkey-setup-button:active {
	opacity: 0.8;
}

.passkey-setup-button:focus-visible,
.passkey-setup-heading button:focus-visible {
	outline: 2px solid var(--h-tab-active);
	outline-offset: 3px;
}

.passkey-setup-modal {
	--height: auto;
}

.passkey-setup-sheet {
	padding: 20px 20px calc(24px + env(safe-area-inset-bottom));
	color: var(--h-fg-primary);
	background: var(--h-bg-card);
}

.passkey-setup-heading {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 16px;
}

.passkey-setup-heading h2 {
	flex: 1;
	min-width: 0;
	font-size: 18px;
	font-weight: 800;
	line-height: 1.4;
}

.passkey-setup-heading button {
	display: grid;
	flex: 0 0 44px;
	width: 44px;
	height: 44px;
	place-items: center;
	border-radius: 12px;
	background: var(--h-bg-card-inner);
}

.passkey-setup-sheet :deep(.passkey-card) {
	padding: 0;
	background: transparent;
	box-shadow: none;
}

.passkey-setup-sheet :deep(.passkey-title),
.passkey-setup-sheet :deep(.device-name) {
	color: var(--h-fg-primary);
}

.passkey-setup-sheet :deep(.passkey-subtitle),
.passkey-setup-sheet :deep(.register-hint),
.passkey-setup-sheet :deep(.device-date) {
	color: var(--h-fg-secondary);
}

.passkey-setup-sheet :deep(.passkey-icon),
.passkey-setup-sheet :deep(.registered-info) {
	background: var(--h-bg-card-inner);
}

.passkey-setup-sheet :deep(.passkey-icon svg) {
	color: var(--h-tab-active);
}

.passkey-setup-sheet :deep(.register-btn) {
	background: var(--h-scan-bg);
	color: var(--h-scan-fg);
	box-shadow: none;
}
</style>
