<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<header class="chat-header">
				<router-link :to="{ name: 'Home' }" class="chat-return">
					<Icon icon="lucide-chevron-left" class="h-5 w-5" aria-hidden="true" />
					<span>{{ __("Back to attendance") }}</span>
				</router-link>
				<h1 class="chat-title">{{ __("Chat") }}</h1>
			</header>
		</ion-header>
		<ion-content class="ion-no-padding" :scroll-y="false">
			<iframe
				v-if="active"
				src="/raven/dm-channel"
				:title="__('Chat')"
				class="chat-frame"
				allow="clipboard-write"
			/>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { inject, ref } from "vue"
import { IonPage, IonHeader, IonContent, onIonViewWillEnter, onIonViewDidLeave } from "@ionic/vue"
import { Icon } from "frappe-ui"

const __ = inject("$translate")
const active = ref(false)

onIonViewWillEnter(() => { active.value = true })
onIonViewDidLeave(() => { active.value = false })
</script>

<style scoped>
.chat-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 4px 16px;
	padding-top: calc(4px + var(--ion-safe-area-top, 0px));
	background: var(--h-bg-page, #f1eee7);
	color: var(--h-fg-primary, #0a0a0a);
	border-bottom: 1px solid var(--h-bd-default, #e3dfd4);
}
.chat-return {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	min-height: 48px;
	font-size: 14px;
	font-weight: 500;
}
.chat-return:active {
	opacity: 0.65;
}
.chat-title {
	margin: 0;
	font-size: 16px;
	font-weight: 600;
}
.chat-frame {
	display: block;
	width: 100%;
	height: 100%;
	border: 0;
}
</style>
