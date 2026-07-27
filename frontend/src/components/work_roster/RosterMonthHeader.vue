<template>
	<header class="month-header">
		<button type="button" :aria-label="labels.previousMonth" @click="emit('previous')">
			<span aria-hidden="true">‹</span>
		</button>

		<div class="month-copy">
			<h2>{{ monthTitle || `${year}年${month}月` }}</h2>
			<p>
				<span v-if="selectableDepartment" class="department-picker">
					<select
						:value="departmentCategory || 'Office'"
						:aria-label="labels.departmentSelector"
						@change="emit('update:departmentCategory', $event.target.value)"
					>
						<option value="Office">{{ labels.departmentOffice }}</option>
						<option value="Production">{{ labels.departmentProduction }}</option>
					</select>
					<span aria-hidden="true">⌄</span>
				</span>
				<span v-else>{{ departmentLabel }}</span>
				<span aria-hidden="true">·</span>
				<span :class="{ published }">
					{{ published ? labels.published : labels.periodMissing }}
				</span>
			</p>
		</div>

		<button type="button" :aria-label="labels.nextMonth" @click="emit('next')">
			<span aria-hidden="true">›</span>
		</button>
	</header>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	year: {
		type: Number,
		required: true,
	},
	month: {
		type: Number,
		required: true,
	},
	monthTitle: {
		type: String,
		default: "",
	},
	departmentCategory: {
		type: String,
		default: "",
	},
	selectableDepartment: {
		type: Boolean,
		default: false,
	},
	published: {
		type: Boolean,
		default: false,
	},
	labels: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["previous", "next", "update:departmentCategory"])
const departmentLabel = computed(() =>
	props.departmentCategory === "Production"
		? props.labels.departmentProduction
		: props.labels.departmentOffice
)
</script>

<style scoped>
.month-header {
	display: grid;
	grid-template-columns: 40px minmax(0, 1fr) 40px;
	align-items: center;
	gap: 8px;
}

button {
	display: grid;
	width: 40px;
	height: 40px;
	place-items: center;
	padding: 0;
	color: var(--h-fg-primary, #0a0a0a);
	font-size: 28px;
	line-height: 1;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 12px;
}

button:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 2px;
}

.month-copy {
	min-width: 0;
	text-align: center;
}

.month-copy h2 {
	margin: 0;
	color: var(--h-fg-primary, #0a0a0a);
	font-size: 18px;
	font-weight: 750;
	line-height: 1.25;
}

.month-copy p {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 5px;
	margin: 4px 0 0;
	color: var(--h-fg-secondary, #64748b);
	font-size: 11px;
	line-height: 1.3;
}

.month-copy .published {
	color: var(--h-summary-shift-fg, #15803d);
	font-weight: 700;
}

.department-picker {
	position: relative;
	display: inline-flex;
	align-items: center;
}

.department-picker select {
	max-width: 92px;
	padding: 0 14px 0 0;
	overflow: hidden;
	color: inherit;
	font: inherit;
	font-weight: 700;
	text-overflow: ellipsis;
	background: transparent;
	border: 0;
	border-radius: 4px;
	appearance: none;
}

.department-picker span {
	position: absolute;
	right: 0;
	pointer-events: none;
}

.department-picker select:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 2px;
}
</style>
