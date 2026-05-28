<template>
	<section class="home-stats-capsule">
		<div class="stats-capsule-label">ALL-TIME</div>
		<div class="stats-capsule-items">
			<div class="stats-capsule-item">
				<span>{{ label("totalHours") }}</span>
				<strong
					>{{ formatNumber(props.stats?.total_hours) }}<small>{{ label("hours") }}</small></strong
				>
			</div>
			<div class="stats-capsule-divider" aria-hidden="true"></div>
			<div class="stats-capsule-item">
				<span>{{ label("totalPresent") }}</span>
				<strong
					>{{ formatNumber(props.stats?.total_present_days)
					}}<small>{{ label("days") }}</small></strong
				>
			</div>
		</div>
	</section>
</template>

<script setup>
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
	totalHours: { zh: "累计工时", ja: "累計時間", en: "Total Hours" },
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
</script>

<style scoped>
.home-stats-capsule {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 14px;
	border: 1px solid #ede9dd;
	border-radius: 999px;
	background: #ffffff;
	padding: 10px 14px;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 18px rgba(15, 23, 42, 0.04);
}

.stats-capsule-label {
	flex: 0 0 auto;
	border-radius: 999px;
	background: #0a0a0a;
	padding: 7px 10px;
	font-size: 10px;
	line-height: 1;
	font-weight: 900;
	color: #ffffff;
}

.stats-capsule-items {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 10px;
	min-width: 0;
	flex: 1;
}

.stats-capsule-item {
	min-width: 0;
	text-align: right;
}

.stats-capsule-item span {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 10px;
	line-height: 1.2;
	font-weight: 800;
	color: var(--h-fg-secondary);
}

.stats-capsule-item strong {
	display: block;
	margin-top: 3px;
	font-size: 17px;
	line-height: 1;
	font-weight: 900;
	color: var(--h-fg-primary);
	font-variant-numeric: tabular-nums;
}

.stats-capsule-item small {
	margin-left: 2px;
	font-size: 10px;
	font-weight: 800;
	color: var(--h-fg-secondary);
}

.stats-capsule-divider {
	width: 1px;
	height: 30px;
	background: var(--h-bd-subtle);
}
</style>
