<template>
	<button
		v-if="!cell.empty"
		ref="button"
		type="button"
		class="roster-day"
		:class="dayClasses"
		:aria-label="cell.ariaLabel"
		@click="emit('select', cell)"
	>
		<span class="roster-day-number">{{ cell.day }}</span>
		<span v-if="cell.event" class="roster-day-event">
			{{ cell.event.title }}
		</span>
		<span v-if="scope === 'mine' && cell.data?.my_shift" class="roster-my-time">
			{{ compactTime(cell.data.my_shift.scheduled_time) }}
		</span>
		<span v-else-if="scope === 'mine'" class="roster-rest">
			{{ labels.rest }}
		</span>
		<span v-else-if="cell.data?.actual_count > 0" class="roster-counts">
			<span>
				{{ labels.actualShort }}
				{{ cell.data.actual_count }}
			</span>
			<span v-if="departmentCategory === 'Production' && cell.data.equivalent_count != null">
				{{ labels.equivalentShort }}
				{{ Number(cell.data.equivalent_count).toFixed(1) }}
			</span>
		</span>
		<span v-else class="roster-rest">{{ labels.emptyShort }}</span>
	</button>
</template>

<script setup>
import { computed, ref } from "vue"

const props = defineProps({
	cell: {
		type: Object,
		required: true,
	},
	scope: {
		type: String,
		required: true,
	},
	departmentCategory: {
		type: String,
		default: "",
	},
	labels: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["select"])
const button = ref(null)

const dayClasses = computed(() => ({
	today: props.cell.isToday,
	sunday: props.cell.isSunday,
	saturday: props.cell.isSaturday,
	holiday: props.cell.isHoliday,
	"weekly-off": props.cell.isWeeklyOff,
	event: Boolean(props.cell.event),
}))

function compactTime(value) {
	if (!value) return props.labels.customTime
	return String(value)
		.split("-")
		.map((part) => {
			const [hour, minute] = part.split(":")
			const normalizedHour = String(Number(hour))
			return minute === "00" ? normalizedHour : `${normalizedHour}:${minute}`
		})
		.join("-")
}

function focus() {
	button.value?.focus()
}

defineExpose({ focus })
</script>

<style scoped>
.roster-day {
	position: relative;
	display: flex;
	flex-direction: column;
	align-items: stretch;
	justify-content: flex-start;
	width: 100%;
	min-width: 0;
	min-height: 44px;
	aspect-ratio: 0.78;
	padding: 5px 3px 4px;
	overflow: hidden;
	color: var(--h-fg-primary, #0a0a0a);
	text-align: left;
	background: var(--h-bg-card, #ffffff);
	border: 1px solid var(--h-bd-subtle, #ede9dd);
	border-radius: 8px;
}

.roster-day:focus-visible {
	z-index: 1;
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 1px;
}

.roster-day.today {
	border-color: var(--h-tab-active, #2563eb);
	box-shadow: inset 0 0 0 1px var(--h-tab-active, #2563eb);
}

.roster-day.sunday,
.roster-day.saturday,
.roster-day.holiday {
	background: color-mix(in srgb, var(--h-chip-off-bg, #f4f4f5) 72%, var(--h-bg-card, #ffffff));
}

.roster-day.event {
	border-top: 3px solid var(--roster-event-color, #f59e0b);
	padding-top: 3px;
}

.roster-day-number {
	font-size: clamp(11px, 3.2vw, 13px);
	font-weight: 750;
	line-height: 1;
}

.roster-day-event {
	margin-top: 3px;
	overflow: hidden;
	color: var(--h-summary-warn-fg, #92400e);
	font-size: clamp(7px, 2.3vw, 9px);
	font-weight: 700;
	line-height: 1.15;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.roster-my-time,
.roster-rest {
	margin-top: auto;
	overflow: hidden;
	color: var(--h-fg-secondary, #64748b);
	font-size: clamp(8px, 2.5vw, 10px);
	font-weight: 650;
	line-height: 1.15;
	text-align: center;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.roster-my-time {
	color: var(--h-summary-shift-fg, #15803d);
}

.roster-counts {
	display: grid;
	gap: 1px;
	margin-top: auto;
	color: var(--h-fg-secondary, #64748b);
	font-size: clamp(7px, 2.35vw, 9px);
	font-weight: 700;
	line-height: 1.15;
	text-align: center;
	white-space: nowrap;
}

.roster-counts span:last-child {
	color: var(--h-summary-shift-fg, #15803d);
}
</style>
