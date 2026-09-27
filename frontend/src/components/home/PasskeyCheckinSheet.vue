<template>
	<ion-modal
		:is-open="isOpen"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
		class="passkey-sheet-modal"
		@didDismiss="emit('dismiss')"
	>
		<div class="passkey-sheet">
			<div class="passkey-sheet-icon" :class="`is-${variant}`">
				<Icon :icon="content.icon" class="h-7 w-7" />
			</div>
			<h2 class="passkey-sheet-title">{{ content.title }}</h2>
			<p v-if="content.body" class="passkey-sheet-body">{{ content.body }}</p>
			<div class="passkey-sheet-actions">
				<button
					v-for="action in content.actions"
					:key="action.id"
					type="button"
					class="passkey-sheet-button"
					:class="action.primary ? 'is-primary' : 'is-secondary'"
					@click="emit('action', action.id)"
				>
					{{ action.label }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed } from "vue"
import { IonModal } from "@ionic/vue"
import { Icon } from "frappe-ui"

import { getSheetContent } from "@/utils/passkeyCheckin"

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	variant: { type: String, default: "first_time" },
	lang: { type: String, default: "zh" },
	locationLabel: { type: String, default: "" },
	locationFailed: { type: Boolean, default: false },
	message: { type: String, default: "" },
})

const emit = defineEmits(["action", "dismiss"])

const content = computed(() =>
	getSheetContent(props.variant, props.lang, {
		locationLabel: props.locationLabel,
		locationFailed: props.locationFailed,
		message: props.message,
	})
)
</script>

<style scoped>
.passkey-sheet-modal {
	--height: auto;
}

.passkey-sheet {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	padding: 28px 20px calc(24px + env(safe-area-inset-bottom));
	text-align: center;
	background: var(--h-scan-bg);
	color: var(--h-scan-fg);
}

.passkey-sheet-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 56px;
	height: 56px;
	border-radius: 18px;
	background: var(--h-scan-icon-bg);
}

.passkey-sheet-title {
	font-size: 18px;
	font-weight: 900;
	line-height: 1.3;
}

.passkey-sheet-body {
	max-width: 320px;
	font-size: 14px;
	line-height: 1.6;
	color: var(--h-scan-fg-sub);
}

.passkey-sheet-actions {
	display: flex;
	flex-direction: column;
	gap: 10px;
	width: min(100%, 360px);
	margin-top: 8px;
}

.passkey-sheet-button {
	min-height: 48px;
	border-radius: 14px;
	font-size: 15px;
	font-weight: 800;
}

.passkey-sheet-button.is-primary {
	background: var(--h-scan-fg);
	color: var(--h-scan-bg);
}

.passkey-sheet-button.is-secondary {
	border: 1px solid var(--h-scan-bd);
	background: transparent;
	color: var(--h-scan-fg);
}
</style>
