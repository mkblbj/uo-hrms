<template>
	<ion-modal
		:is-open="isOpen"
		:backdrop-dismiss="mandatory"
		:can-dismiss="canDismiss"
		class="photo-sheet-modal"
		@didDismiss="onDismissed"
	>
		<div class="photo-sheet">
			<header v-if="step === 'edit'" class="photo-sheet-header">
				<h2 class="photo-sheet-title">{{ heading }}</h2>
			</header>

			<div class="photo-sheet-body" :class="{ 'is-intro': step === 'intro' }">
				<div class="photo-sheet-inner">
					<template v-if="step === 'intro'">
						<div class="photo-sheet-avatar" aria-hidden="true">
							<img v-if="currentPhoto" :src="currentPhoto" alt="" />
							<Icon v-else icon="lucide-circle-user-round" class="h-12 w-12" />
						</div>
						<h2 class="photo-sheet-title">{{ heading }}</h2>
						<p v-if="mandatory" class="photo-sheet-required">{{ t("mandatoryNotice") }}</p>
						<p v-if="mode === 'reminder'" class="photo-sheet-notice">{{ content.lead }}</p>
						<p v-else class="photo-sheet-lead">{{ t("changeLead") }}</p>
					</template>

					<ProfilePhotoEditor
						v-else
						ref="editorRef"
						:src="sourceUrl"
						:lang="lang"
						@ready="onEditorReady"
						@error="onEditorError"
					/>

					<p v-if="errorMessage" class="photo-sheet-error" role="alert">{{ errorMessage }}</p>
				</div>
			</div>

			<footer class="photo-sheet-actions">
				<template v-if="step === 'intro'">
					<p class="photo-sheet-formats">{{ t("supportedFormats") }}</p>
					<button type="button" class="photo-sheet-button is-primary" @click="pick('camera')">
						<Icon icon="lucide-camera" class="h-5 w-5" />
						{{ t("takePhoto") }}
					</button>
					<button type="button" class="photo-sheet-button is-secondary" @click="pick('library')">
						<Icon icon="lucide-image" class="h-5 w-5" />
						{{ t("choosePhoto") }}
					</button>
					<button
						v-if="!mandatory"
						type="button"
						class="photo-sheet-link"
						:disabled="remaining > 0"
						@click="close(dismissEvent)"
					>
						{{ laterLabel }}
					</button>
				</template>
				<template v-else>
					<button
						type="button"
						class="photo-sheet-button is-primary"
						:disabled="uploading || !editorReady"
						@click="upload"
					>
						{{ uploading ? t("uploading") : t("usePhoto") }}
					</button>
					<button
						type="button"
						class="photo-sheet-button is-secondary"
						:disabled="uploading"
						@click="backToIntro"
					>
						{{ t("chooseAgain") }}
					</button>
				</template>
			</footer>

			<input
				ref="cameraInput"
				class="photo-sheet-input"
				type="file"
				accept="image/*"
				capture="user"
				tabindex="-1"
				aria-hidden="true"
				@change="onFileChosen"
			/>
			<input
				ref="libraryInput"
				class="photo-sheet-input"
				type="file"
				accept="image/*"
				tabindex="-1"
				aria-hidden="true"
				@change="onFileChosen"
			/>
		</div>
	</ion-modal>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { IonModal } from "@ionic/vue"
import { Icon } from "frappe-ui"

import ProfilePhotoEditor from "@/components/profile/ProfilePhotoEditor.vue"
import {
	getReminderContent,
	pickPhotoCopy,
	preparePhotoUpload,
	uploadProfilePhoto,
} from "@/utils/profilePhoto"

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	mandatory: { type: Boolean, default: false },
	// reminder：头像更换和期限提醒；change：个人页里换头像
	mode: { type: String, default: "reminder" },
	status: { type: Object, default: null },
	currentPhoto: { type: String, default: "" },
	lang: { type: String, default: "zh" },
	// 「稍后再说」要等这么多秒才能点（每次打开应用的提醒用；自己点开的为 0）
	snoozeDelay: { type: Number, default: 0 },
})

const emit = defineEmits(["snooze", "cancel", "uploaded"])

const step = ref("intro")
const sourceUrl = ref("")
const sourceFile = ref(null)
const editorReady = ref(false)
const uploading = ref(false)
const errorMessage = ref("")
const editorRef = ref(null)
const cameraInput = ref(null)
const libraryInput = ref(null)
let closedByUs = false

const t = (key) => pickPhotoCopy(key, props.lang)
const content = computed(() => getReminderContent(props.status, props.lang))
const heading = computed(() => {
	if (step.value === "edit") return t("editTitle")
	return props.mode === "reminder" ? content.value.title : t("changeTitle")
})
const dismissEvent = computed(() => (props.mode === "reminder" ? "snooze" : "cancel"))

const remaining = ref(0)
let countdownTimer = null
const laterLabel = computed(() => {
	const label = props.mode === "reminder" ? t("later") : t("cancel")
	return remaining.value > 0 ? `${label} (${remaining.value}s)` : label
})

function stopCountdown() {
	if (countdownTimer) clearInterval(countdownTimer)
	countdownTimer = null
}

// 按结束时刻算剩余秒数：手机切到后台计时器变慢也不会多等
function startCountdown() {
	stopCountdown()
	const delay = Math.max(0, Number(props.snoozeDelay) || 0)
	const endsAt = Date.now() + delay * 1000
	const tick = () => {
		remaining.value = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000))
		if (remaining.value === 0) stopCountdown()
	}
	tick()
	if (remaining.value > 0) countdownTimer = setInterval(tick, 250)
}

watch(
	() => [props.isOpen, props.snoozeDelay],
	([open]) => {
		if (open) startCountdown()
		else {
			stopCountdown()
			remaining.value = 0
		}
	},
	{ immediate: true }
)

function pick(kind) {
	errorMessage.value = ""
	const input = kind === "camera" ? cameraInput.value : libraryInput.value
	input?.click()
}

function onFileChosen(event) {
	const file = event.target.files?.[0]
	event.target.value = ""
	if (!file) return
	releaseSource()
	sourceFile.value = file
	sourceUrl.value = URL.createObjectURL(file)
	errorMessage.value = ""
	step.value = "edit"
}

function onEditorReady() {
	editorReady.value = true
	errorMessage.value = ""
}

function onEditorError(reason) {
	editorReady.value = false
	errorMessage.value = t(reason === "tooSmall" ? "tooSmall" : "readFailed")
}

async function upload() {
	if (!editorRef.value || uploading.value) return
	uploading.value = true
	errorMessage.value = ""
	try {
		const { blob, crop } = await preparePhotoUpload(sourceFile.value, editorRef.value)
		const photo = await uploadProfilePhoto(blob, { crop })
		closedByUs = true
		emit("uploaded", photo)
		reset()
	} catch (error) {
		errorMessage.value = error?.message || t("uploadFailed")
	} finally {
		uploading.value = false
	}
}

function backToIntro() {
	releaseSource()
	errorMessage.value = ""
	step.value = "intro"
}

function close(event) {
	if (props.mandatory || remaining.value > 0) return
	closedByUs = true
	emit(event)
	reset()
}

function canDismiss() {
	// 强制模式让 Ionic 接管返回键和 Esc，实际关闭统一由这个条件决定。
	return (!props.mandatory && remaining.value === 0) || !props.isOpen || closedByUs
}

// 安卓返回键这类从外面关掉的，按「稍后再说 / 取消」算
function onDismissed() {
	if (!closedByUs && props.isOpen) emit(dismissEvent.value)
	closedByUs = false
	reset()
}

function releaseSource() {
	if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
	sourceUrl.value = ""
	sourceFile.value = null
	editorReady.value = false
}

function reset() {
	releaseSource()
	errorMessage.value = ""
	uploading.value = false
	step.value = "intro"
}

onBeforeUnmount(() => {
	closedByUs = true
	stopCountdown()
	releaseSource()
})
</script>

<style scoped>
/* 全局把弹窗设成了随内容高度，这里要全屏 */
.photo-sheet-modal {
	--height: 100%;
	--width: 100%;
}

/* 铺满整个弹窗：中间滚动，按钮固定在底部 */
.photo-sheet {
	position: absolute;
	inset: 0;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	color: var(--h-fg-primary);
	background: var(--h-bg-page);
}

.photo-sheet-header {
	padding: calc(20px + env(safe-area-inset-top)) 20px 8px;
	text-align: center;
}

.photo-sheet-title {
	font-size: 21px;
	font-weight: 900;
	line-height: 1.35;
	text-align: center;
	text-wrap: balance;
}

.photo-sheet-body {
	display: flex;
	flex: 1;
	min-height: 0;
	flex-direction: column;
	padding: 12px 20px 16px;
	overflow-y: auto;
	-webkit-overflow-scrolling: touch;
}

/* 提醒页没有顶栏，自己让出刘海的位置 */
.photo-sheet-body.is-intro {
	padding-top: calc(20px + env(safe-area-inset-top));
}

/* 内容短时上下居中，长时照常从上往下滚 */
.photo-sheet-inner {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 14px;
	width: 100%;
	margin: auto 0;
}

.photo-sheet-avatar {
	display: grid;
	flex: 0 0 auto;
	width: 112px;
	height: 112px;
	place-items: center;
	overflow: hidden;
	color: var(--h-fg-muted);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 50%;
}

.photo-sheet-avatar img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.photo-sheet-lead {
	max-width: 320px;
	color: var(--h-fg-secondary);
	font-size: 15px;
	line-height: 1.7;
	text-align: center;
}

.photo-sheet-required {
	width: min(100%, 420px);
	padding: 12px 16px;
	border-radius: 12px;
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	font-size: 15px;
	font-weight: 700;
	line-height: 1.5;
	text-align: center;
}

/* 提醒正文比较长，放进卡片里左对齐，好读 */
.photo-sheet-notice {
	width: min(100%, 420px);
	padding: 14px 16px;
	color: var(--h-fg-primary);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 16px;
	font-size: 15px;
	line-height: 1.75;
	text-align: left;
}

.photo-sheet-error {
	width: min(100%, 420px);
	padding: 10px 14px;
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border: 1px solid var(--h-summary-warn-bd);
	border-radius: 12px;
	font-size: 13.5px;
	line-height: 1.5;
	text-align: center;
}

.photo-sheet-actions {
	display: flex;
	flex-direction: column;
	gap: 10px;
	width: 100%;
	padding: 12px max(20px, calc((100% - 420px) / 2)) calc(16px + env(safe-area-inset-bottom));
	border-top: 1px solid var(--h-bd-subtle);
}

.photo-sheet-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	min-height: 50px;
	border-radius: 14px;
	font-size: 15px;
	font-weight: 800;
}

.photo-sheet-formats {
	color: var(--h-fg-secondary);
	font-size: 13px;
	line-height: 1.5;
	text-align: center;
}

.photo-sheet-button:disabled {
	opacity: 0.55;
}

.photo-sheet-button.is-primary {
	color: var(--h-scan-fg);
	background: var(--h-scan-bg);
}

.photo-sheet-button.is-secondary {
	color: var(--h-fg-primary);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
}

.photo-sheet-link {
	min-height: 40px;
	color: var(--h-fg-secondary);
	font-size: 14px;
	font-weight: 600;
}

.photo-sheet-link:disabled {
	opacity: 0.5;
}

/* 不能用 display:none，部分 iPhone 上点不开选图 */
.photo-sheet-input {
	position: absolute;
	width: 1px;
	height: 1px;
	overflow: hidden;
	opacity: 0;
	pointer-events: none;
}
</style>
