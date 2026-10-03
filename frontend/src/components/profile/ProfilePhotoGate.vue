<template>
	<section v-if="blocked && !needsPhoto" class="photo-access-check" aria-live="polite">
		<p :role="status.error ? 'alert' : 'status'">
			{{ t(status.error ? "photoCheckFailed" : "checkingPhoto") }}
		</p>
		<button v-if="status.error" type="button" @click="recheck">
			{{ t("photoCheckRetry") }}
		</button>
	</section>
	<ProfilePhotoSheet
		:is-open="needsPhoto"
		:mandatory="true"
		mode="reminder"
		:status="status.data"
		:current-photo="status.data?.photo || ''"
		:lang="lang"
		@uploaded="onUploaded"
	/>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from "vue"
import { toast } from "frappe-ui"

import ProfilePhotoSheet from "@/components/profile/ProfilePhotoSheet.vue"
import { profilePhotoStatus as status, refreshProfilePhoto } from "@/data/profilePhoto"
import { session } from "@/data/session"
import { isPhotoDoneRemembered, pickPhotoCopy, rememberPhotoDone } from "@/utils/profilePhoto"

const props = defineProps({ lang: { type: String, default: "zh" } })
const emit = defineEmits(["blocked"])
const t = (key) => pickPhotoCopy(key, props.lang)
const storage = (() => {
	try {
		return window.localStorage
	} catch (_) {
		return null
	}
})()
// 这台手机上确认过头像已设好：不用等检查，后台照常核对；核对出没设好再拦
const remembered = isPhotoDoneRemembered(storage, session.user)
const needsPhoto = computed(() => Boolean(status.data?.required && !status.data?.has_photo))
const blocked = computed(() => needsPhoto.value || (!status.data && !remembered))

watch(blocked, (value) => emit("blocked", value), { immediate: true, flush: "sync" })
watch(
	() => status.data,
	(data) => {
		if (data) rememberPhotoDone(storage, session.user, !data.required || data.has_photo)
	},
	{ flush: "sync" }
)

// 返回前台时检查最新状态；状态仍未完成不会重置取景和上传步骤。
function recheck() {
	if (status.loading) return
	return status.reload().catch(() => {})
}

function onVisibilityChange() {
	if (document.visibilityState === "visible") recheck()
}

function onUploaded(photo) {
	// 只有上传接口已成功保存后才放行，失败时强制弹窗保持打开。
	status.abort()
	status.setData({ ...status.data, has_photo: true, temporary: false, photo })
	toast.success(t("uploaded"))
	refreshProfilePhoto()
	status.reload().catch(() => {})
}

status.abort()
status.reset()
recheck()

onMounted(() => {
	document.addEventListener("visibilitychange", onVisibilityChange)
	window.addEventListener("online", recheck)
})

onBeforeUnmount(() => {
	document.removeEventListener("visibilitychange", onVisibilityChange)
	window.removeEventListener("online", recheck)
	status.abort()
})
</script>

<style scoped>
.photo-access-check {
	position: fixed;
	inset: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 20px;
	padding: 24px;
	color: var(--h-fg-primary);
	background: var(--h-bg-page);
	text-align: center;
}

.photo-access-check button {
	min-width: 160px;
	min-height: 48px;
	padding: 12px 24px;
	border-radius: 12px;
	color: var(--h-scan-fg);
	background: var(--h-scan-bg);
	font-weight: 700;
}
</style>
