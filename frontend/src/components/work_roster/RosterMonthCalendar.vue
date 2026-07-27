<template>
	<section class="roster-calendar" role="grid" :style="{ '--roster-week-count': weekCount }">
		<div class="roster-weekdays" role="row">
			<div
				v-for="(label, index) in weekdayLabels"
				:key="`${label}-${index}`"
				class="roster-weekday"
				:class="{ sunday: index === 0, saturday: index === 6 }"
				role="columnheader"
			>
				{{ label }}
			</div>
		</div>

		<div class="roster-days">
			<template v-for="(cell, index) in cells" :key="cell.dateStr || `empty-${index}`">
				<div v-if="cell.empty" class="roster-empty-cell" aria-hidden="true"></div>
				<RosterDayCell
					v-else
					:ref="(element) => setDayRef(cell.dateStr, element)"
					:cell="cell"
					:scope="scope"
					:department-category="departmentCategory"
					:labels="labels"
					@select="emit('select-day', $event)"
				/>
			</template>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue"

import RosterDayCell from "@/components/work_roster/RosterDayCell.vue"

const props = defineProps({
	cells: {
		type: Array,
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
	weekdayLabels: {
		type: Array,
		required: true,
	},
	labels: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["select-day"])
const dayRefs = new Map()
const weekCount = computed(() => Math.max(5, Math.ceil(props.cells.length / 7)))

function setDayRef(dateStr, element) {
	if (element) {
		dayRefs.set(dateStr, element)
	} else {
		dayRefs.delete(dateStr)
	}
}

function focusDate(dateStr) {
	dayRefs.get(dateStr)?.focus()
}

defineExpose({ focusDate })
</script>

<style scoped>
.roster-calendar {
	display: grid;
	flex: 1;
	grid-template-rows: auto minmax(0, 1fr);
	width: 100%;
	min-height: 0;
	padding: 8px;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 16px;
}

.roster-weekdays,
.roster-days {
	display: grid;
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 3px;
	width: 100%;
}

.roster-weekdays {
	margin-bottom: 5px;
}

.roster-days {
	min-height: 0;
	grid-template-rows: repeat(var(--roster-week-count), minmax(44px, 1fr));
}

.roster-weekday {
	padding: 2px 0 4px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 10px;
	font-weight: 700;
	line-height: 1;
	text-align: center;
}

.roster-weekday.sunday,
.roster-weekday.saturday {
	color: var(--h-summary-warn-fg, #92400e);
}

.roster-empty-cell {
	min-width: 0;
	min-height: 44px;
}

@media (max-width: 340px) {
	.roster-calendar {
		padding: 6px;
	}

	.roster-weekdays,
	.roster-days {
		gap: 2px;
	}
}
</style>
