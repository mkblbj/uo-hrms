<template>
	<div class="rounded-2xl bg-white p-4 shadow-sm">
		<div class="text-sm font-semibold text-gray-900">{{ copy.title }}</div>
		<div class="mt-1 text-xs text-gray-500">{{ copy.description }}</div>
		<div class="mt-4 grid gap-2">
			<button
				v-for="option in PWA_LANGUAGE_OPTIONS"
				:key="option.value"
				type="button"
				class="flex items-center justify-between rounded-xl border px-3 py-3 text-sm"
				:class="option.value === currentLanguage ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 bg-white text-gray-700'"
				@click="selectLanguage(option.value)"
			>
				<span>{{ option.label }}</span>
				<span v-if="option.value === currentLanguage">✓</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

import {
	PWA_LANGUAGE_OPTIONS,
	changeLanguage,
	getServerLanguage,
	getStoredLanguage,
} from "@/utils/language"
import { getLanguageCardCopy } from "@/utils/homeExperience"

const currentLanguage = computed(() => getStoredLanguage() || getServerLanguage())
const copy = computed(() => getLanguageCardCopy(window.frappe?.boot?.lang || "zh"))

function selectLanguage(language) {
	if (language === currentLanguage.value) return
	changeLanguage(language)
}
</script>
