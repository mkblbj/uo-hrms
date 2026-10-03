<template>
	<section
		v-if="showCard"
		class="photo-prompt"
		:class="{ 'is-overdue': card.overdue }"
		aria-live="polite"
	>
		<div class="photo-prompt-icon" aria-hidden="true">
			<Icon icon="lucide-circle-user-round" class="h-5 w-5" />
		</div>
		<div class="photo-prompt-content">
			<strong>{{ card.title }}</strong>
			<p>{{ card.message }}</p>
			<button type="button" class="photo-prompt-button" @click="checkProfilePhoto">
				{{ card.action }}
			</button>
		</div>
	</section>
</template>

<script setup>
import { computed } from "vue"
import { Icon } from "frappe-ui"

import { openPhotoReminder, profilePhotoStatus as status } from "@/data/profilePhoto"
import { getPromptCardContent } from "@/utils/profilePhoto"

const props = defineProps({
	lang: { type: String, default: "zh" },
})

const showCard = computed(() => Boolean(status.data?.required && !status.data?.has_photo))
const card = computed(() => getPromptCardContent(status.data, props.lang))

// 自己点开的提醒不用倒计时；顺便刷新一下状态
function checkProfilePhoto() {
	openPhotoReminder(0)
	status.reload().catch(() => {})
}
</script>

<style scoped>
.photo-prompt {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	width: 100%;
	padding: 16px;
	color: var(--h-fg-primary);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 16px;
}

.photo-prompt.is-overdue {
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border-color: var(--h-summary-warn-bd);
}

.photo-prompt-icon {
	display: grid;
	flex: 0 0 44px;
	width: 44px;
	height: 44px;
	place-items: center;
	color: var(--h-tab-active);
	background: var(--h-bg-card-inner);
	border-radius: 12px;
}

.is-overdue .photo-prompt-icon {
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border: 1px solid var(--h-summary-warn-bd);
}

.photo-prompt-content {
	flex: 1;
	min-width: 0;
}

.photo-prompt-content strong {
	display: block;
	font-size: 16px;
	font-weight: 800;
	line-height: 1.4;
}

.photo-prompt-content p {
	margin: 4px 0 0;
	color: var(--h-fg-secondary);
	font-size: 14px;
	line-height: 1.5;
}

.is-overdue .photo-prompt-content p {
	color: var(--h-summary-warn-fg);
}

.photo-prompt-button {
	width: 100%;
	min-height: 44px;
	margin-top: 12px;
	border-radius: 12px;
	color: var(--h-scan-fg);
	background: var(--h-scan-bg);
	font-size: 15px;
	font-weight: 800;
}
</style>
