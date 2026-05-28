<template>
	<div class="home-scan-action-bar">
		<button
			type="button"
			class="scan-action-button"
			:class="{ 'is-disabled': isDisabled }"
			:disabled="isDisabled"
			@click="$emit('scan')"
		>
			<span class="scan-action-icon" aria-hidden="true">
				<FeatherIcon :name="iconName" class="h-5 w-5" />
			</span>
			<span class="scan-action-copy">
				<strong>{{ actionTitle }}</strong>
				<small>{{ actionDescription }}</small>
			</span>
			<FeatherIcon name="chevron-right" class="scan-action-arrow" />
		</button>
	</div>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

const CHECK_IN = "CHECK_IN"
const CHECK_OUT = "CHECK_OUT"
const DONE = "DONE"

const props = defineProps({
	cta: {
		type: Object,
		default: null,
	},
	workStatus: {
		type: Object,
		default: null,
	},
	lang: {
		type: String,
		default: "zh",
	},
	disabled: {
		type: Boolean,
		default: false,
	},
})

defineEmits(["scan"])

const labels = {
	CHECK_IN: {
		title: { zh: "扫码出勤", ja: "QRコードで出勤", en: "Scan to Check In" },
		description: {
			zh: "打开相机进行打卡",
			ja: "カメラを起動して打刻します",
			en: "Open camera to record attendance",
		},
	},
	CHECK_OUT: {
		title: { zh: "扫码退勤", ja: "QRコードで退勤", en: "Scan to Check Out" },
		description: {
			zh: "打开相机完成退勤",
			ja: "カメラを起動して退勤します",
			en: "Open camera to finish check-out",
		},
	},
	DONE: {
		title: { zh: "今日已完成", ja: "本日は完了", en: "Done for Today" },
		description: {
			zh: "今日勤怠已结束",
			ja: "本日の勤怠は終了しました",
			en: "Today's attendance is closed",
		},
	},
}

function pick(key, field) {
	return labels[key]?.[field]?.[props.lang] || labels[key]?.[field]?.zh || ""
}

const actionMode = computed(() => {
	if (props.cta?.action === "OUT") return CHECK_OUT
	if (props.cta?.action === "IN") return CHECK_IN
	if (props.workStatus?.status === "off_work") return DONE
	return CHECK_IN
})
const isDone = computed(() => actionMode.value === DONE)
const isDisabled = computed(() => props.disabled || !props.cta)
const iconName = computed(() => {
	if (isDone.value) return "check-circle"
	return actionMode.value === CHECK_OUT ? "log-out" : "camera"
})
const actionTitle = computed(() => {
	if (!isDone.value && props.cta?.title) return props.cta.title
	return pick(actionMode.value, "title")
})
const actionDescription = computed(() => {
	if (!isDone.value && props.cta?.description) return props.cta.description
	return pick(actionMode.value, "description")
})
</script>

<style scoped>
.home-scan-action-bar {
	position: fixed;
	right: 16px;
	bottom: 10px;
	left: 16px;
	z-index: 25;
	pointer-events: none;
}

.scan-action-button {
	display: flex;
	align-items: center;
	gap: 12px;
	width: min(100%, 520px);
	min-height: 54px;
	margin: 0 auto;
	border: 1px solid var(--h-scan-bd);
	border-radius: 20px;
	background: var(--h-scan-bg);
	color: var(--h-scan-fg);
	padding: 10px 14px 10px 12px;
	box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18), 0 0 0 0.5px var(--h-scan-bd);
	backdrop-filter: blur(18px);
	pointer-events: auto;
	transition: transform 0.14s ease, box-shadow 0.14s ease, background 0.14s ease;
}

.scan-action-button:active:not(.is-disabled) {
	transform: scale(0.985);
	box-shadow: 0 10px 24px rgba(15, 23, 42, 0.22);
}

.scan-action-button.is-disabled {
	background: var(--h-scan-disabled-bg);
	box-shadow: 0 10px 22px rgba(100, 116, 139, 0.2);
}

.scan-action-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 38px;
	width: 38px;
	height: 38px;
	border-radius: 14px;
	background: var(--h-scan-icon-bg);
}

.scan-action-copy {
	flex: 1;
	min-width: 0;
	text-align: left;
}

.scan-action-copy strong,
.scan-action-copy small {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.scan-action-copy strong {
	font-size: 16px;
	line-height: 1.2;
	font-weight: 900;
}

.scan-action-copy small {
	margin-top: 3px;
	font-size: 12px;
	line-height: 1.25;
	font-weight: 700;
	color: var(--h-scan-fg-sub);
}

.scan-action-arrow {
	flex: 0 0 auto;
	width: 18px;
	height: 18px;
	opacity: 0.75;
}
</style>
