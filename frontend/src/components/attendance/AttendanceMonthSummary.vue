<template>
	<section class="attn-summary">
		<header class="attn-summary-head">
			<span class="attn-summary-kicker">{{ monthTitle }}</span>
			<strong>{{ t("summary.title") }}</strong>
		</header>

		<div class="attn-summary-metrics">
			<div class="attn-summary-metric">
				<span>{{ t("summary.totalHours") }}</span>
				<strong>{{ summary.hours }}<small>h</small></strong>
			</div>
			<div class="attn-summary-metric">
				<span>{{ t("summary.workDays") }}</span>
				<strong>{{ summary.workDays }}</strong>
			</div>
			<div class="attn-summary-metric">
				<span>{{ t("summary.avgHours") }}</span>
				<strong>{{ summary.avg }}<small>h</small></strong>
			</div>
		</div>

		<div v-if="progress.visible" class="attn-progress">
			<div class="attn-progress-label">
				{{ t("summary.progress", { done: progress.done, total: progress.total }) }}
			</div>
			<div
				class="attn-progress-track"
				role="progressbar"
				:aria-valuenow="progress.percent"
				aria-valuemin="0"
				aria-valuemax="100"
			>
				<div class="attn-progress-fill" :style="{ width: `${progress.percent}%` }"></div>
			</div>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue"

import { getAttendanceCopy } from "@/utils/attendanceCalendarCopy"
import { computeProgress, summarizeMonth } from "@/utils/attendanceCalendarState"

const props = defineProps({
	cells: { type: Array, required: true },
	scheduledDays: { type: Number, default: 0 },
	monthTitle: { type: String, default: "" },
	lang: { type: String, default: "zh" },
})

const summary = computed(() => summarizeMonth(props.cells))
const progress = computed(() => computeProgress(props.cells, props.scheduledDays))

function t(key, params) {
	return getAttendanceCopy(key, props.lang, params)
}
</script>

<style scoped>
.attn-summary {
	padding: 12px 14px;
	background: var(--h-bg-card, #ffffff);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 16px;
}

.attn-summary-head {
	display: flex;
	align-items: baseline;
	gap: 8px;
	margin-bottom: 10px;
}

.attn-summary-kicker {
	color: var(--h-fg-secondary, #64748b);
	font-size: 11px;
	font-variant-numeric: tabular-nums;
}

.attn-summary-head strong {
	font-size: 15px;
	font-weight: 700;
}

.attn-summary-metrics {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 8px;
}

.attn-summary-metric {
	display: flex;
	flex-direction: column;
	gap: 3px;
}

.attn-summary-metric span {
	color: var(--h-fg-secondary, #64748b);
	font-size: 11px;
}

.attn-summary-metric strong {
	font-size: 20px;
	font-weight: 750;
	line-height: 1;
}

.attn-summary-metric small {
	margin-left: 1px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 11px;
	font-weight: 600;
}

.attn-progress {
	margin-top: 12px;
}

.attn-progress-label {
	margin-bottom: 5px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 11px;
}

.attn-progress-track {
	width: 100%;
	height: 6px;
	overflow: hidden;
	background: var(--h-track-bg, #e8e5dc);
	border-radius: 999px;
}

.attn-progress-fill {
	height: 100%;
	background: linear-gradient(
		90deg,
		var(--h-track-fill-start, #86efac),
		var(--h-track-fill-end, #16a34a)
	);
	border-radius: inherit;
	transition: width 240ms ease;
}

@media (prefers-reduced-motion: reduce) {
	.attn-progress-fill {
		transition: none;
	}
}
</style>
