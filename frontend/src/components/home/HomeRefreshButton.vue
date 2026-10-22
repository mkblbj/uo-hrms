<template>
	<button
		type="button"
		class="home-refresh"
		:title="label"
		:aria-label="label"
		@click="reloadPage"
	>
		<svg
			class="h-5 w-5"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<polyline points="23 4 23 10 17 10" />
			<polyline points="1 20 1 14 7 14" />
			<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
		</svg>
	</button>
</template>

<script setup>
import { computed } from "vue"
import { resolveHomeLanguage } from "@/utils/homeExperience"

const labels = { zh: "刷新页面", ja: "ページを再読み込み", en: "Refresh page" }
const label = computed(() => labels[resolveHomeLanguage()] || labels.zh)

function reloadPage() {
	window.location.reload()
}
</script>

<style scoped>
.home-refresh {
	position: relative;
	display: flex;
	flex-shrink: 0;
	align-items: center;
	justify-content: center;
	width: 36px;
	height: 36px;
	border: 1px solid var(--h-bd-default);
	border-radius: 9999px;
	background: var(--h-bg-elevated);
	color: var(--h-fg-secondary);
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
	cursor: pointer;
}

.home-refresh::before {
	position: absolute;
	inset: -4px;
	content: "";
}

.home-refresh:active {
	transform: scale(0.95);
}

.home-refresh:focus-visible {
	outline: 2px solid var(--h-fg-secondary);
	outline-offset: 3px;
}
</style>
