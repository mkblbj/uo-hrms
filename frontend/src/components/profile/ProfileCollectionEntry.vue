<template>
	<router-link v-if="enabled" :to="{ name: 'ProfileCollection' }" class="profile-collection-entry">
		<span class="profile-entry-icon" aria-hidden="true"
			><Icon icon="lucide-contact-round" class="h-6 w-6"
		/></span>
		<span class="profile-entry-copy"
			><strong>{{ t("title") }}</strong
			><span>{{ t("entryLead") }}</span></span
		>
		<span class="profile-entry-action"
			>{{ t("entryAction") }}<Icon icon="lucide-chevron-right" class="h-4 w-4" aria-hidden="true"
		/></span>
	</router-link>
</template>

<script setup>
import { inject, ref, watch } from "vue"
import { call, Icon } from "frappe-ui"
import { resolveHomeLanguage } from "@/utils/homeExperience"
import { PROFILE_COLLECTION_STATUS, profileCollectionCopy } from "@/utils/profileCollection"

const session = inject("$session")
const enabled = ref(false)
const lang = resolveHomeLanguage(window.frappe?.boot)
const t = (key) => profileCollectionCopy(key, lang)
watch(
	() => session.user,
	async (user) => {
		enabled.value = false
		if (!user || user === "Guest") return
		try {
			const status = await call(PROFILE_COLLECTION_STATUS)
			if (session.user === user) enabled.value = status.enabled === true
		} catch {
			enabled.value = false
		}
	},
	{ immediate: true }
)
</script>

<style scoped>
.profile-collection-entry {
	display: flex;
	align-items: center;
	gap: 12px;
	width: 100%;
	min-height: 78px;
	margin-bottom: 12px;
	padding: 15px 14px;
	border: 1px solid var(--h-bd-default, #d9e3d9);
	border-radius: 14px;
	background: var(--h-bg-elevated, #fff);
	text-decoration: none;
}
.profile-entry-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	width: 40px;
	height: 40px;
	border-radius: 12px;
	background: #e5f1e8;
	color: #23755b;
}
.profile-entry-copy {
	display: flex;
	flex: 1;
	min-width: 0;
	flex-direction: column;
	gap: 5px;
}
.profile-entry-copy strong {
	font-size: 15px;
	color: var(--h-fg-primary, #161b1a);
}
.profile-entry-copy > span {
	font-size: 12px;
	line-height: 1.5;
	color: var(--h-fg-secondary, #64706a);
}
.profile-entry-action {
	display: flex;
	align-items: center;
	flex-shrink: 0;
	gap: 2px;
	font-size: 13px;
	font-weight: 600;
	color: #23755b;
}
.profile-collection-entry:focus-visible {
	outline: 2px solid #23755b;
	outline-offset: 3px;
}
</style>
