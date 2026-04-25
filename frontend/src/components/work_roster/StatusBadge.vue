<template>
	<span
		:class="[
			'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
			statusClasses[status] || 'bg-gray-100 text-gray-600',
		]"
	>
		{{ statusLabels[status]?.[getLang()] || statusLabels[status]?.zh || __(status) }}
	</span>
</template>

<script setup>
import { inject } from "vue"

defineProps({
	status: { type: String, required: true },
})

const __ = inject("$translate")

const statusClasses = {
	Draft: "bg-gray-100 text-gray-600",
	Collecting: "bg-blue-100 text-blue-700",
	Scheduling: "bg-yellow-100 text-yellow-700",
	Published: "bg-green-100 text-green-700",
	Closed: "bg-gray-100 text-gray-500",
}

const statusLabels = {
	Draft: { zh: "草稿", ja: "下書き", en: "Draft" },
	Collecting: { zh: "征集中", ja: "募集中", en: "Collecting" },
	Scheduling: { zh: "排班中", ja: "編成中", en: "Scheduling" },
	Published: { zh: "已发布", ja: "公開済み", en: "Published" },
	Closed: { zh: "已关闭", ja: "終了", en: "Closed" },
}

function getLang() {
	return frappe?.boot?.lang || "zh"
}
</script>
