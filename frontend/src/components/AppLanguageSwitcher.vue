<template>
	<div class="relative" ref="menuRef">
		<button
			type="button"
			class="flex h-9 min-w-[2.75rem] items-center justify-center rounded-full bg-gray-100 px-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-200"
			aria-haspopup="menu"
			:aria-expanded="isOpen"
			@click="toggleMenu"
		>
			{{ currentOption.shortLabel }}
		</button>

		<div
			v-if="isOpen"
			class="absolute right-0 top-11 z-20 w-40 rounded-2xl border border-gray-200 bg-white p-2 shadow-xl"
			role="menu"
		>
			<button
				v-for="option in PWA_LANGUAGE_OPTIONS"
				:key="option.value"
				type="button"
				class="flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm text-gray-700 transition hover:bg-gray-100"
				:class="option.value === currentLanguage ? 'bg-gray-100 font-semibold text-gray-900' : ''"
				@click="selectLanguage(option.value)"
			>
				<span>{{ option.label }}</span>
				<span v-if="option.value === currentLanguage">✓</span>
			</button>
		</div>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import {
	PWA_LANGUAGE_OPTIONS,
	changeLanguage,
	getServerLanguage,
	getStoredLanguage,
} from "@/utils/language"

const menuRef = ref(null)
const isOpen = ref(false)

const currentLanguage = computed(() => getStoredLanguage() || getServerLanguage())
const currentOption = computed(() => {
	return (
		PWA_LANGUAGE_OPTIONS.find((option) => option.value === currentLanguage.value) ||
		PWA_LANGUAGE_OPTIONS[2]
	)
})

function toggleMenu() {
	isOpen.value = !isOpen.value
}

function closeMenu() {
	isOpen.value = false
}

function selectLanguage(language) {
	if (language === currentLanguage.value) {
		closeMenu()
		return
	}
	changeLanguage(language)
}

function handleClickOutside(event) {
	if (!menuRef.value?.contains(event.target)) {
		closeMenu()
	}
}

onMounted(() => {
	document.addEventListener("click", handleClickOutside)
})

onBeforeUnmount(() => {
	document.removeEventListener("click", handleClickOutside)
})
</script>
