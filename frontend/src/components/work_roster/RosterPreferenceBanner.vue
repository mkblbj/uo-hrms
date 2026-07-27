<template>
	<section v-if="notice" class="preference-banner" :class="{ submitted: notice.has_preference }">
		<div class="preference-copy">
			<strong>
				{{ notice.status === "Scheduling" ? labels.scheduling : notice.title }}
			</strong>
			<span v-if="notice.status === 'Collecting' && notice.preference_deadline">
				{{ deadlineText }}
			</span>
			<span v-if="notice.status === 'Collecting' && notice.has_preference" class="submitted-label">
				{{ labels.submitted }}
			</span>
		</div>

		<router-link
			v-if="notice.status === 'Collecting'"
			:to="`/work-roster/preference/${notice.period}`"
		>
			{{ notice.has_preference ? labels.editPreference : labels.submitPreference }}
		</router-link>
	</section>
</template>

<script setup>
import { computed } from "vue"

const props = defineProps({
	notice: {
		type: Object,
		default: null,
	},
	labels: {
		type: Object,
		required: true,
	},
})

const deadlineText = computed(() => {
	const deadline = props.notice?.preference_deadline || ""
	const template = props.labels.deadline || ""
	return template.includes("{date}")
		? template.replace("{date}", deadline)
		: `${template} ${deadline}`.trim()
})
</script>

<style scoped>
.preference-banner {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	min-height: 58px;
	padding: 10px 12px;
	color: var(--h-summary-warn-fg, #92400e);
	background: var(--h-summary-warn-bg, #fffbeb);
	border: 1px solid var(--h-summary-warn-bd, #fde68a);
	border-radius: 14px;
}

.preference-banner.submitted {
	color: var(--h-fg-primary, #0a0a0a);
	background: var(--h-bg-card, #ffffff);
	border-color: var(--h-bd-default, #e3dfd4);
}

.preference-copy {
	display: flex;
	flex: 1;
	flex-wrap: wrap;
	align-items: baseline;
	gap: 3px 8px;
	min-width: 0;
}

.preference-copy strong {
	width: 100%;
	overflow: hidden;
	font-size: 13px;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.preference-copy span {
	font-size: 12px;
	color: var(--h-fg-secondary, #64748b);
}

.submitted-label {
	font-weight: 600;
	color: var(--h-summary-shift-fg, #15803d) !important;
}

a {
	flex: 0 0 auto;
	min-height: 36px;
	padding: 8px 11px;
	color: var(--h-fg-on-dark, #ffffff);
	font-size: 12px;
	font-weight: 700;
	line-height: 20px;
	text-decoration: none;
	background: var(--h-tab-active, #2563eb);
	border-radius: 10px;
}

a:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 2px;
}
</style>
