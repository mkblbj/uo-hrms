<template>
	<div class="roster-tabs" role="tablist" :aria-label="labels.viewSelector">
		<button
			v-for="scope in scopes"
			:key="scope"
			type="button"
			role="tab"
			:aria-selected="modelValue === scope"
			:class="{ active: modelValue === scope }"
			@click="emit('update:modelValue', scope)"
		>
			{{ scope === "mine" ? labels.myShift : labels.departmentShift }}
		</button>
	</div>
</template>

<script setup>
defineProps({
	modelValue: {
		type: String,
		required: true,
		validator: (value) => ["mine", "department"].includes(value),
	},
	labels: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["update:modelValue"])
const scopes = ["mine", "department"]
</script>

<style scoped>
.roster-tabs {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 4px;
	padding: 4px;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 14px;
}

button {
	min-width: 0;
	min-height: 42px;
	padding: 8px 10px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 14px;
	font-weight: 600;
	background: transparent;
	border: 0;
	border-radius: 10px;
	transition: background-color 150ms ease, color 150ms ease, box-shadow 150ms ease;
}

button.active {
	color: var(--h-tab-active, #2563eb);
	background: var(--h-bg-card, #ffffff);
	box-shadow: 0 1px 3px rgba(15, 23, 42, 0.12);
}

button:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 1px;
}
</style>
