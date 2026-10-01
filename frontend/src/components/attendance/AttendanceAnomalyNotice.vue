<template>
	<button
		v-if="count > 0"
		type="button"
		class="attn-notice"
		:aria-label="`${noticeText}, ${actionText}`"
		@click="emit('open')"
	>
		<span class="attn-notice-dot" aria-hidden="true"></span>
		<span class="attn-notice-text">{{ noticeText }}</span>
		<span class="attn-notice-action">{{ actionText }}</span>
	</button>
</template>

<script setup>
import { computed } from "vue"

import { getAttendanceCopy } from "@/utils/attendanceCalendarCopy"

const props = defineProps({
	count: { type: Number, default: 0 },
	lang: { type: String, default: "zh" },
})

const emit = defineEmits(["open"])

const noticeText = computed(() =>
	getAttendanceCopy("anomaly.notice", props.lang, { count: props.count })
)
const actionText = computed(() => getAttendanceCopy("anomaly.action", props.lang))
</script>

<style scoped>
.attn-notice {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	min-height: 44px;
	padding: 10px 14px;
	color: var(--h-attn-anomaly-fg, #991b1b);
	text-align: left;
	background: var(--h-attn-anomaly-bg, #fee2e2);
	border: 1px solid transparent;
	border-radius: 14px;
}

.attn-notice:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 2px;
}

.attn-notice-dot {
	flex: none;
	width: 7px;
	height: 7px;
	background: currentColor;
	border-radius: 50%;
}

.attn-notice-text {
	flex: 1;
	min-width: 0;
	font-size: 13px;
	font-weight: 650;
}

.attn-notice-action {
	flex: none;
	font-size: 12px;
	font-weight: 700;
	text-decoration: underline;
}
</style>
