<template>
	<button
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
import { computed, onBeforeUnmount, onMounted } from "vue"
import { useRouter } from "vue-router"
import { createResource } from "frappe-ui"

import { getStatusChipMeta } from "@/utils/homeExperience"

const router = useRouter()

const workStatus = createResource({
	url: "hrms.api.get_employee_work_status",
	auto: true,
	cache: false,
})

const lang = computed(() => window.frappe?.boot?.lang || "zh")
const meta = computed(() =>
	getStatusChipMeta(Boolean(workStatus.data?.is_working), lang.value),
)

const reload = () => workStatus.reload()

onMounted(() => {
	window.addEventListener("checkin-status-changed", reload)
})

onBeforeUnmount(() => {
	window.removeEventListener("checkin-status-changed", reload)
})
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
	background: rgba(16, 185, 129, 0.12);
	color: #047857;
}

.status-chip.off {
	background: rgba(148, 163, 184, 0.14);
	color: #475569;
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
