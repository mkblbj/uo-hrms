<template>
	<div class="home-stats-grid">
		<div v-for="card in cards" :key="card.key" class="home-stat-card">
			<div class="home-stat-icon" :class="card.tone">
				<FeatherIcon :name="card.icon" class="h-4 w-4" />
			</div>
			<div class="home-stat-value">
				{{ card.value }}<span class="home-stat-unit">{{ card.unit }}</span>
			</div>
			<div class="home-stat-label">{{ card.label }}</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const props = defineProps({
	stats: {
		type: Object,
		default: null,
	},
	lang: {
		type: String,
		default: "zh",
	},
})

const labels = {
	monthHours: { zh: "本月工时", ja: "今月の勤務時間", en: "This Month" },
	monthPresent: { zh: "本月出勤", ja: "今月の出勤", en: "Days Present" },
	totalHours: { zh: "累计总工时", ja: "累計勤務時間", en: "Total Hours" },
	totalPresent: { zh: "累计出勤", ja: "累計出勤", en: "Total Days" },
	hours: { zh: "h", ja: "h", en: "h" },
	days: { zh: "天", ja: "日", en: "d" },
}

function label(key) {
	return labels[key]?.[props.lang] || labels[key]?.zh || key
}

function formatNumber(value) {
	const numeric = Number(value || 0)
	return Number.isInteger(numeric) ? numeric.toLocaleString() : numeric.toFixed(1)
}

const cards = computed(() => [
	{
		key: "month_hours",
		icon: "clock",
		tone: "blue",
		value: formatNumber(props.stats?.month_hours),
		unit: label("hours"),
		label: label("monthHours"),
	},
	{
		key: "month_present",
		icon: "check-circle",
		tone: "green",
		value: formatNumber(props.stats?.month_present),
		unit: label("days"),
		label: label("monthPresent"),
	},
	{
		key: "total_hours",
		icon: "bar-chart-2",
		tone: "purple",
		value: formatNumber(props.stats?.total_hours),
		unit: label("hours"),
		label: label("totalHours"),
	},
	{
		key: "total_present_days",
		icon: "calendar",
		tone: "amber",
		value: formatNumber(props.stats?.total_present_days),
		unit: label("days"),
		label: label("totalPresent"),
	},
])
</script>

<style scoped>
.home-stats-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 10px;
}

.home-stat-card {
	min-height: 112px;
	border-radius: 16px;
	background: #ffffff;
	padding: 14px;
	box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.02);
}

.home-stat-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	border-radius: 8px;
	margin-bottom: 10px;
}

.home-stat-icon.blue {
	background: #eff6ff;
	color: #2563eb;
}

.home-stat-icon.green {
	background: #ecfdf5;
	color: #10b981;
}

.home-stat-icon.purple {
	background: #f3e8ff;
	color: #7c3aed;
}

.home-stat-icon.amber {
	background: #fffbeb;
	color: #d97706;
}

.home-stat-value {
	font-size: 28px;
	line-height: 1;
	font-weight: 800;
	color: #0f172a;
	font-variant-numeric: tabular-nums;
}

.home-stat-unit {
	margin-left: 2px;
	font-size: 13px;
	font-weight: 600;
	color: #64748b;
}

.home-stat-label {
	margin-top: 6px;
	font-size: 12px;
	font-weight: 600;
	color: #64748b;
}
</style>
