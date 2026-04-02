<template>
	<span
		:class="[
			'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
			statusClasses[status] || 'bg-gray-100 text-gray-600',
		]"
	>
		{{ statusLabels[status] || status }}
	</span>
</template>

<script setup>
import { inject } from "vue"

const __ = inject("$translate")

defineProps({
	status: { type: String, required: true },
})

const statusClasses = {
	Draft: "bg-gray-100 text-gray-600",
	Collecting: "bg-blue-100 text-blue-700",
	Scheduling: "bg-yellow-100 text-yellow-700",
	Published: "bg-green-100 text-green-700",
	Closed: "bg-gray-100 text-gray-500",
}

const statusLabels = {
	Draft: __("Draft"),
	Collecting: __("Collecting"),
	Scheduling: __("Scheduling"),
	Published: __("Published"),
	Closed: __("Closed"),
}
</script>
