<template>
	<button
		type="button"
		class="theme-toggle"
		:title="isDark ? t.toLight : t.toDark"
		@click="toggle"
	>
		<svg v-if="isDark" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
			<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v2.25M18.364 5.636l-1.591 1.591M21 12h-2.25M18.364 18.364l-1.591-1.591M12 18.75V21M7.227 16.773l-1.591 1.591M5.25 12H3M7.227 7.227L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0z" />
		</svg>
		<svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
			<path stroke-linecap="round" stroke-linejoin="round" d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z" />
		</svg>
	</button>
</template>

<script setup>
import { useTheme } from "@/composables/useTheme"

const { isDark, toggle } = useTheme()

const lang = (window.frappe?.boot?.lang || "zh").split("-")[0]
const t = {
	zh: { toDark: "切换暗色", toLight: "切换亮色" },
	ja: { toDark: "ダークモード", toLight: "ライトモード" },
	en: { toDark: "Dark mode", toLight: "Light mode" },
}[lang] || { toDark: "Dark mode", toLight: "Light mode" }
</script>

<style scoped>
.theme-toggle {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 36px;
	height: 36px;
	border-radius: 9999px;
	border: 1px solid var(--h-bd-default);
	background: var(--h-bg-elevated);
	color: var(--h-fg-secondary);
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
	transition: background 0.2s, color 0.2s, border-color 0.2s;
}

.theme-toggle:active {
	transform: scale(0.95);
}
</style>
