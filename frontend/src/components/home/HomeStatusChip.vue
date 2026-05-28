<template>
	<button
		v-if="meta"
		type="button"
		class="status-chip"
		:class="meta.tone"
		@click="router.push({ name: meta.routeName })"
	>
		<span class="status-dot"></span>
		<span class="status-text">{{ meta.label }}</span>
	</button>
</template>

<script setup>
import { computed } from "vue"
import { useRouter } from "vue-router"

import {
	getStatusChipMeta,
	resolveHomeLanguage,
} from "@/utils/homeExperience"

const props = defineProps({
	workStatus: {
		type: Object,
		required: true,
	},
})

const router = useRouter()

const lang = computed(() => resolveHomeLanguage(window.frappe?.boot))
const meta = computed(() =>
	getStatusChipMeta(props.workStatus?.data, lang.value),
)
</script>

<style scoped>
.status-chip {
	display: inline-flex;
	align-items: center;
	gap: 0.4rem;
	min-height: 2.25rem;
	padding: 0 0.75rem;
	border-radius: 9999px;
	font-size: 0.75rem;
	font-weight: 700;
	transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.status-chip.working {
	background: var(--h-chip-working-bg);
	color: var(--h-chip-working-fg);
}

.status-chip.off {
	background: var(--h-chip-off-bg);
	color: var(--h-chip-off-fg);
}

.status-chip.pending {
	background: var(--h-chip-pending-bg);
	color: var(--h-chip-pending-fg);
}

.status-chip:active {
	transform: scale(0.98);
}

.status-dot {
	width: 0.5rem;
	height: 0.5rem;
	border-radius: 9999px;
	background: currentColor;
}
</style>
