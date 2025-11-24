<template>
	<div class="stats-card" :class="colorClass">
		<div class="stats-header">
			<FeatherIcon :name="icon" class="stats-icon" />
			<span class="stats-label">{{ label }}</span>
		</div>
		<div class="stats-value">{{ value }}</div>
		<div v-if="subtitle" class="stats-subtitle">{{ subtitle }}</div>
	</div>
</template>

<script setup>
import { FeatherIcon } from "frappe-ui"
import { computed } from "vue"

const props = defineProps({
	label: String,
	value: [String, Number],
	subtitle: String,
	icon: String,
	color: {
		type: String,
		default: "blue"
	}
})

const colorClass = computed(() => `color-${props.color}`)
</script>

<style scoped>
.stats-card {
	background: white;
	border-radius: 10px;
	padding: 12px 14px;
	box-shadow: 0 2px 6px rgba(0,0,0,0.05);
	border-left: 3px solid;
	transition: all 0.2s;
}

.stats-card:active {
	transform: scale(0.98);
}

.stats-card.color-blue {
	border-left-color: #667eea;
}

.stats-card.color-green {
	border-left-color: #10b981;
}

.stats-card.color-orange {
	border-left-color: #f59e0b;
}

.stats-card.color-purple {
	border-left-color: #8b5cf6;
}

.stats-card.color-red {
	border-left-color: #ef4444;
}

.stats-header {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-bottom: 8px;
}

.stats-icon {
	width: 16px;
	height: 16px;
	opacity: 0.7;
}

.stats-card.color-blue .stats-icon {
	color: #667eea;
}

.stats-card.color-green .stats-icon {
	color: #10b981;
}

.stats-card.color-orange .stats-icon {
	color: #f59e0b;
}

.stats-card.color-purple .stats-icon {
	color: #8b5cf6;
}

.stats-card.color-red .stats-icon {
	color: #ef4444;
}

.stats-label {
	font-size: 11px;
	font-weight: 500;
	color: #6b7280;
}

.stats-value {
	font-size: 22px;
	font-weight: 700;
	color: #111827;
	line-height: 1;
	margin-bottom: 2px;
}

.stats-subtitle {
	font-size: 10px;
	color: #9ca3af;
}
</style>

