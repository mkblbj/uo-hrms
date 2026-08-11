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
		<span v-if="scope === 'mine' && cell.data?.my_shift" class="roster-primary">
			{{ compactTime(cell.data.my_shift.scheduled_time) }}
		</span>
		<span v-else-if="scope === 'mine'" class="roster-primary blank">
			{{ labels.rest }}
		</span>
		<span v-else-if="cell.data?.actual_count > 0" class="roster-primary">
			{{ cell.data.actual_count }}
			<small v-if="departmentCategory === 'Production' && cell.data.equivalent_count != null">
				{{ labels.equivalentShort }}
				{{ Number(cell.data.equivalent_count).toFixed(1) }}
			</small>
			<small v-else>{{ labels.actualShort }}</small>
		</span>
		<span v-else class="roster-primary blank">{{ labels.emptyShort }}</span>
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
	gap: 2px;
	width: 100%;
	height: 100%;
	min-width: 0;
	min-height: 56px;
	padding: 5px 4px;
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

.roster-day-number {
	font-size: clamp(12px, 3.2vw, 14px);
	font-weight: 500;
	line-height: 1;
}

.roster-day-event {
	overflow: hidden;
	padding: 1px 2px;
	color: var(--h-summary-warn-fg, #92400e);
	font-size: clamp(10px, 2.7vw, 12px);
	font-weight: 650;
	line-height: 1.35;
	text-align: center;
	text-overflow: ellipsis;
	white-space: nowrap;
	background: var(--h-summary-warn-bg, #fffbeb);
	border-radius: 4px;
}

.roster-primary {
	display: flex;
	flex: 1;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-height: 0;
	overflow: hidden;
	color: var(--h-summary-shift-fg, #15803d);
	font-size: clamp(16px, 4.6vw, 19px);
	font-weight: 500;
	line-height: 1;
	white-space: nowrap;
}

.roster-primary.blank {
	color: var(--h-fg-secondary, #64748b);
	font-size: clamp(14px, 4vw, 16px);
	background: var(--h-chip-off-bg, #f4f4f5);
	border-radius: 6px;
}

.roster-primary small {
	margin-top: 2px;
	color: var(--h-fg-secondary, #64748b);
	font-size: clamp(10px, 2.7vw, 12px);
	font-weight: 650;
	line-height: 1;
}
</style>
