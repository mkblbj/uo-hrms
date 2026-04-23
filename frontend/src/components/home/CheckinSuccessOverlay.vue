<template>
	<ion-modal
		:is-open="isOpen"
		:backdrop-dismiss="false"
		@didDismiss="handleDidDismiss"
		class="success-overlay-modal"
	>
		<div class="success-overlay" :class="model.variant">
			<div class="success-status">{{ model.statusLabel }}</div>
			<div class="success-motion">
				<CheckInRunnerAnimation v-if="model.variant === 'checkin'" />
				<CheckOutCoffeeAnimation v-else />
			</div>
			<h2 class="success-title">{{ model.title }}</h2>
			<p v-if="model.description" class="success-description">
				{{ model.description }}
			</p>
			<div class="success-info-card">
				<div v-for="row in model.infoRows" :key="row.label" class="success-info-row">
					<span class="success-info-label">{{ row.label }}</span>
					<span class="success-info-value">{{ row.value }}</span>
				</div>
			</div>
			<div v-if="actionsVisible" class="success-actions">
				<button type="button" class="success-primary" @click="$emit('primary')">
					{{ model.primaryLabel }}
				</button>
				<button type="button" class="success-secondary" @click="$emit('close')">
					{{ model.secondaryLabel }}
				</button>
			</div>
		</div>
	</ion-modal>
</template>

<script setup>
import { IonModal } from "@ionic/vue"

import CheckInRunnerAnimation from "@/components/home/success/CheckInRunnerAnimation.vue"
import CheckOutCoffeeAnimation from "@/components/home/success/CheckOutCoffeeAnimation.vue"

defineProps({
	isOpen: Boolean,
	actionsVisible: Boolean,
	model: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["primary", "close"])

function handleDidDismiss(event) {
	emit("close", event)
}
</script>

<style scoped>
ion-modal.success-overlay-modal {
	--width: 100%;
	--height: 100%;
	--border-radius: 0;
	--box-shadow: none;
	--background: transparent;
	--backdrop-opacity: 0.56;
}

ion-modal.success-overlay-modal::part(content) {
	background: transparent;
}

.success-overlay {
	min-height: 100dvh;
	padding: 28px 24px 36px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	color: #f8fafc;
}

.success-overlay.checkin {
	background: radial-gradient(circle at top, rgba(125, 211, 252, 0.3), transparent 38%),
		linear-gradient(180deg, #0f172a 0%, #172554 52%, #1d4ed8 100%);
}

.success-overlay.checkout {
	background: radial-gradient(circle at top, rgba(251, 191, 36, 0.24), transparent 40%),
		linear-gradient(180deg, #3f1d0f 0%, #7c2d12 48%, #ea580c 100%);
}

.success-status {
	padding: 8px 16px;
	border-radius: 999px;
	font-size: 13px;
	font-weight: 600;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	background: rgba(255, 255, 255, 0.14);
	box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}

.success-motion {
	width: 100%;
	max-width: 240px;
	height: 170px;
	margin: 28px 0 12px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.success-title {
	margin: 0;
	font-size: 28px;
	line-height: 1.15;
	font-weight: 700;
}

.success-description {
	margin: 12px 0 0;
	max-width: 320px;
	font-size: 15px;
	line-height: 1.6;
	color: rgba(248, 250, 252, 0.88);
}

.success-info-card {
	width: min(100%, 360px);
	margin-top: 22px;
	padding: 18px 18px 10px;
	border-radius: 24px;
	background: rgba(15, 23, 42, 0.22);
	backdrop-filter: blur(20px);
	box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08), 0 20px 60px rgba(15, 23, 42, 0.2);
}

.success-info-row {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	padding-bottom: 12px;
	margin-bottom: 12px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.success-info-row:last-child {
	margin-bottom: 0;
	padding-bottom: 0;
	border-bottom: 0;
}

.success-info-label {
	font-size: 13px;
	color: rgba(248, 250, 252, 0.72);
}

.success-info-value {
	flex: 1;
	text-align: right;
	font-size: 14px;
	font-weight: 600;
	color: #ffffff;
}

.success-actions {
	width: min(100%, 360px);
	display: flex;
	flex-direction: column;
	gap: 12px;
	margin-top: 24px;
}

.success-primary,
.success-secondary {
	width: 100%;
	border: 0;
	border-radius: 18px;
	padding: 15px 18px;
	font-size: 15px;
	font-weight: 600;
	cursor: pointer;
	transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.success-primary {
	color: #0f172a;
	background: #ffffff;
	box-shadow: 0 12px 30px rgba(15, 23, 42, 0.18);
}

.success-secondary {
	color: #f8fafc;
	background: rgba(255, 255, 255, 0.12);
	box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.success-primary:active,
.success-secondary:active {
	transform: scale(0.98);
}

@media (min-width: 768px) {
	.success-overlay {
		padding-top: 44px;
		padding-bottom: 44px;
	}

	.success-motion {
		max-width: 280px;
		height: 190px;
	}
}
</style>
