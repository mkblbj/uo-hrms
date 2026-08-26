<template>
	<button
		ref="button"
		type="button"
		class="attn-day"
		:class="dayClasses"
		:aria-label="ariaLabel"
		@click="emit('select', cell)"
	>
		<span class="attn-day-number">{{ cell.day }}</span>
		<span v-if="cell.calendar_event" class="attn-event">
			{{ cell.calendar_event.title }}
		</span>
		<span v-else class="attn-event is-spacer" aria-hidden="true">&nbsp;</span>
		<span v-if="blockText" class="attn-block" :class="`is-${blockKind}`">
			<span class="attn-block-value">{{ blockText }}</span>
		</span>
		<span v-else class="attn-block is-empty" aria-hidden="true"></span>
	</button>
</template>

<script setup>
import { computed, ref } from "vue"

import { getAttendanceCopy } from "@/utils/attendanceCalendarCopy"
import { formatWorkHours, isOvertime } from "@/utils/attendanceCalendarState"

const props = defineProps({
	cell: { type: Object, required: true },
	lang: { type: String, default: "zh" },
	selected: { type: Boolean, default: false },
})

const emit = defineEmits(["select"])
const button = ref(null)

const blockKind = computed(() => {
	const { state, hours } = props.cell
	if (state === "anomaly") return "anomaly"
	if (state === "holiday") return "holiday"
	if (state === "rest" || state === "leave") return "rest"
	if (state === "work" && isOvertime(hours)) return "overtime"
	if (state === "work" || state === "wfh" || state === "half") return "work"
	return "empty"
})

const blockText = computed(() => {
	const kind = blockKind.value
	if (kind === "empty") return ""
	if (kind === "anomaly") {
		return props.cell.anomaly_label || getAttendanceCopy("legend.anomaly", props.lang)
	}
	if (kind === "holiday") return getAttendanceCopy("badge.holiday", props.lang)
	if (kind === "rest") return getAttendanceCopy("badge.rest", props.lang)
	// A work day with no hours yet is today still in progress — never "off".
	return formatWorkHours(props.cell.hours) || getAttendanceCopy("badge.working", props.lang)
})

const ariaLabel = computed(() => `${props.cell.dateStr} ${blockText.value}`.trim())

const dayClasses = computed(() => ({
	today: props.cell.is_today,
	selected: props.selected,
	sunday: props.cell.weekday === 0,
	saturday: props.cell.weekday === 6,
}))

function focus() {
	button.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
.attn-day {
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: stretch;
	justify-content: flex-start;
	gap: 2px;
	width: 100%;
	height: 100%;
	min-width: 0;
	min-height: 44px;
	padding: 5px 3px;
	overflow: hidden;
	color: var(--h-fg-primary, #0a0a0a);
	text-align: left;
	background: var(--h-bg-card, #ffffff);
	border: 1px solid var(--h-bd-subtle, #ede9dd);
	border-radius: 8px;
}

.attn-day:focus-visible {
	z-index: 1;
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 1px;
}

.attn-day.today,
.attn-day.selected {
	border-color: var(--h-tab-active, #2563eb);
	box-shadow: inset 0 0 0 1px var(--h-tab-active, #2563eb);
}

.attn-day-number {
	font-size: clamp(12px, 3.2vw, 14px);
	font-weight: 500;
	line-height: 1;
}

.attn-day.sunday .attn-day-number {
	color: var(--h-summary-warn-fg, #92400e);
}

.attn-day.saturday .attn-day-number {
	color: var(--h-tab-active, #2563eb);
}

.attn-event {
	overflow: hidden;
	padding: 1px 0;
	color: var(--h-roster-event-fg, #7c3a0c);
	font-size: clamp(7px, 2vw, 9px);
	font-weight: 650;
	line-height: 1.35;
	text-align: center;
	text-overflow: ellipsis;
	white-space: nowrap;
	background: var(--h-roster-event-bg, #fde68a);
	border-radius: 4px;
}

/* Reserves the event row so the block below starts at the same height on every
   cell. Without it a week with a few sale days reads as ragged. */
.attn-event.is-spacer {
	visibility: hidden;
}

.attn-block {
	display: flex;
	flex: 1;
	align-items: center;
	justify-content: center;
	min-height: 0;
	overflow: hidden;
	font-size: clamp(13px, 4.1vw, 18px);
	font-weight: 500;
	line-height: 1;
	border-radius: 6px;
}

.attn-block-value {
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.attn-block.is-work {
	color: var(--h-attn-work-fg, #14532d);
	background: var(--h-attn-work-bg, #dcfce7);
}

.attn-block.is-overtime {
	color: var(--h-attn-overtime-fg, #f0fdf4);
	background: var(--h-attn-overtime-bg, #16a34a);
}

.attn-block.is-anomaly {
	color: var(--h-attn-anomaly-fg, #991b1b);
	font-size: clamp(9px, 2.6vw, 11px);
	background: var(--h-attn-anomaly-bg, #fee2e2);
}

.attn-block.is-rest {
	color: var(--h-attn-rest-fg, #52627a);
	font-size: clamp(13px, 4vw, 16px);
	background: var(--h-attn-rest-bg, #e9edf2);
}

.attn-block.is-holiday {
	color: var(--h-attn-holiday-fg, #9b2c2c);
	font-size: clamp(13px, 4vw, 16px);
	background: var(--h-attn-holiday-bg, #fde8e8);
}

.attn-block.is-empty {
	background: none;
}

@media (max-width: 340px) {
	.attn-day {
		gap: 1px;
		padding: 4px 2px;
	}

	.attn-event.is-spacer {
		display: none;
	}

	.attn-day-number {
		font-size: 11px;
	}

	.attn-block {
		font-size: 12px;
	}
}
</style>
