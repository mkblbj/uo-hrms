<template>
	<ion-page>
		<div class="chat-edge sticky top-0" :style="{ background: ravenSurface }" aria-hidden="true" />
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
import { inject, onBeforeUnmount, ref } from "vue"
import { IonPage, IonContent, onIonViewWillEnter, onIonViewDidLeave } from "@ionic/vue"

import { RAVEN_THEME_KEY, ravenSurfaceColor } from "@/utils/ravenSurface"

const __ = inject("$translate")
const active = ref(false)

// iOS 26+ looks 8px below the top edge for a fixed or sticky element and extends
// its background into the status bar; finding none, it blurs the top of the page.
// The iframe can't play that part, so a thin sticky band does, wearing the colour
// of Raven's own top bar. Raven keeps its own light/dark choice, so the band
// follows it: changes made inside the frame arrive as storage events, and Raven's
// "system" setting tracks the phone.
const colorScheme = window.matchMedia("(prefers-color-scheme: dark)")
const ravenSurface = ref(currentRavenSurface())

function readStoredRavenTheme() {
	try {
		return localStorage.getItem(RAVEN_THEME_KEY)
	} catch {
		return null
	}
}

function currentRavenSurface() {
	return ravenSurfaceColor({ stored: readStoredRavenTheme(), systemDark: colorScheme.matches })
}

function syncRavenSurface() {
	ravenSurface.value = currentRavenSurface()
}

function onStorage(event) {
	// A null key means storage was cleared, which puts Raven back on its default.
	if (event.key === RAVEN_THEME_KEY || event.key === null) syncRavenSurface()
}

window.addEventListener("storage", onStorage)
colorScheme.addEventListener("change", syncRavenSurface)

onIonViewWillEnter(() => {
	syncRavenSurface()
	active.value = true
})
onIonViewDidLeave(() => { active.value = false })

onBeforeUnmount(() => {
	window.removeEventListener("storage", onStorage)
	colorScheme.removeEventListener("change", syncRavenSurface)
})
</script>

<style scoped>
/* Tall enough to cover WebKit's probe 8px below the top edge. */
.chat-edge {
	flex: none;
	height: calc(10px + var(--ion-safe-area-top, 0px));
}
.chat-frame {
	display: block;
	width: 100%;
	height: 100%;
	border: 0;
}
</style>
