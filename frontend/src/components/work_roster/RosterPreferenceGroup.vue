<template>
	<section v-if="group.rows.length" class="pref-card">
		<header class="pref-head">
			<h3>{{ group.title }}</h3>
			<span v-if="group.countText" class="pref-head-count" :class="`is-${group.countTone}`">
				{{ group.countText }}
			</span>
		</header>

		<router-link
			v-for="row in group.rows"
			:key="row.period"
			:to="row.to"
			class="pref-row"
			:class="{ 'is-done': row.done }"
		>
			<span class="pref-row-text">
				<span class="pref-row-title">{{ row.title }}</span>
				<span v-if="row.deadlineText" class="pref-row-sub" :class="{ 'is-urgent': row.urgent }">
					{{ row.deadlineText }}
				</span>
			</span>
			<span class="pref-row-end">
				<Icon v-if="row.done" icon="lucide-check" class="pref-check" aria-hidden="true" />
				<span>{{ row.actionText }}</span>
				<Icon icon="lucide-chevron-right" class="pref-chev" aria-hidden="true" />
			</span>
		</router-link>
	</section>
</template>

<script setup>
import { computed } from "vue"
import { Icon } from "frappe-ui"

import { buildHomePreferenceGroup } from "@/utils/rosterCalendar"

const props = defineProps({
	notices: { type: Array, default: () => [] },
	lang: { type: String, default: "zh" },
	today: { type: String, default: "" },
})

const group = computed(() =>
	buildHomePreferenceGroup(props.notices, { lang: props.lang, today: props.today })
)
</script>

<style scoped>
/* 和首页「シフト案内」的 .roster-card 同一套圆角、边框和阴影 */
.pref-card {
	width: 100%;
	overflow: hidden;
	border: 1px solid var(--h-bd-subtle);
	border-radius: 18px;
	background: var(--h-bg-card);
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 18px rgba(15, 23, 42, 0.04);
}

.pref-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	height: 28px;
	padding: 8px 14px 0;
}

.pref-head h3 {
	margin: 0;
	font-size: 12px;
	line-height: 16px;
	font-weight: 900;
	color: var(--h-fg-secondary);
	white-space: nowrap;
}

.pref-head-count {
	font-size: 11px;
	line-height: 16px;
	font-weight: 800;
	white-space: nowrap;
}

.pref-head-count.is-pending {
	color: var(--h-chip-pending-fg);
}

.pref-head-count.is-done {
	color: var(--h-chip-working-fg);
}

/* 整行就是点击区，行高 44px */
.pref-row {
	position: relative;
	display: flex;
	align-items: center;
	gap: 10px;
	min-height: 44px;
	padding: 6px 12px 6px 14px;
	color: inherit;
	text-decoration: none;
}

.pref-row + .pref-row::before {
	content: "";
	position: absolute;
	top: 0;
	right: 0;
	left: 14px;
	height: 1px;
	background: var(--h-bd-subtle);
}

.pref-row:active {
	background: var(--h-bg-card-inner);
}

.pref-row:focus-visible {
	outline: 2px solid var(--h-tab-active);
	outline-offset: -2px;
	border-radius: 12px;
}

.pref-row-text {
	display: grid;
	flex: 1 1 auto;
	min-width: 0;
}

/* 放不下时折成两行，不把月份截掉（只有窄屏英文会用到） */
.pref-row-title {
	font-size: 14px;
	line-height: 18px;
	font-weight: 700;
	color: var(--h-fg-primary);
	overflow-wrap: anywhere;
}

/* 已提交的月份标题降灰，没交的更显眼 */
.pref-row.is-done .pref-row-title {
	color: var(--h-fg-secondary);
}

.pref-row-sub {
	font-size: 11px;
	line-height: 14px;
	font-weight: 700;
	color: var(--h-fg-secondary);
	white-space: nowrap;
}

.pref-row-sub.is-urgent {
	color: var(--h-chip-pending-fg);
}

.pref-row-end {
	display: inline-flex;
	flex: 0 0 auto;
	align-items: center;
	gap: 4px;
	font-size: 12px;
	line-height: 16px;
	font-weight: 800;
	color: var(--h-tab-active);
	white-space: nowrap;
}

.pref-row.is-done .pref-row-end {
	color: var(--h-chip-working-fg);
}

.pref-check {
	width: 13px;
	height: 13px;
}

.pref-chev {
	width: 16px;
	height: 16px;
	margin-left: 2px;
	color: var(--h-fg-muted);
}
</style>
