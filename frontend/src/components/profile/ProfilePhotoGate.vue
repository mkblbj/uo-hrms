<template>
	<ProfilePhotoSheet
		:is-open="photoReminder.open"
		:snooze-delay="photoReminder.snoozeDelay"
		mode="reminder"
		:status="status.data"
		:current-photo="status.data?.photo || ''"
		:lang="lang"
		@snooze="onSnooze"
		@uploaded="onUploaded"
	/>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from "vue"
import { toast } from "frappe-ui"

import ProfilePhotoSheet from "@/components/profile/ProfilePhotoSheet.vue"
import {
	openPhotoReminder,
	photoReminder,
	profilePhotoStatus as status,
	refreshProfilePhoto,
} from "@/data/profilePhoto"
import { pickPhotoCopy } from "@/utils/profilePhoto"

// 没自己上传头像的员工：每次打开应用弹出提醒，倒计时结束后可以先跳过，不挡打卡和其他页面。
const SNOOZE_DELAY_SECONDS = 30
// 跳过后从后台切回来，离开超过这么久才再提醒（去拍照这类短暂切出不算）
const REMIND_AGAIN_AFTER_MS = 10 * 60 * 1000

const props = defineProps({ lang: { type: String, default: "zh" } })
const t = (key) => pickPhotoCopy(key, props.lang)
const needsPhoto = computed(() => Boolean(status.data?.required && !status.data?.has_photo))
let snoozedAt = 0

function remindIfDue() {
	if (!needsPhoto.value || photoReminder.open) return
	if (snoozedAt && Date.now() - snoozedAt < REMIND_AGAIN_AFTER_MS) return
	openPhotoReminder(SNOOZE_DELAY_SECONDS)
}

watch(
	needsPhoto,
	(value) => {
		if (value) remindIfDue()
		else photoReminder.open = false
	},
	{ flush: "sync" }
)

function onSnooze() {
	photoReminder.open = false
	snoozedAt = Date.now()
}

function recheck() {
	if (status.loading) return
	return status.reload().catch(() => {})
}

function onVisibilityChange() {
	if (document.visibilityState !== "visible") return
	recheck()
	remindIfDue()
}

function onUploaded(photo) {
	status.abort()
	status.setData({ ...status.data, has_photo: true, temporary: false, photo })
	photoReminder.open = false
	toast.success(t("uploaded"))
	refreshProfilePhoto()
	status.reload().catch(() => {})
}

status.abort()
status.reset()
photoReminder.open = false
recheck()

onMounted(() => {
	document.addEventListener("visibilitychange", onVisibilityChange)
	window.addEventListener("online", recheck)
})

onBeforeUnmount(() => {
	document.removeEventListener("visibilitychange", onVisibilityChange)
	window.removeEventListener("online", recheck)
	status.abort()
	photoReminder.open = false
})
</script>
