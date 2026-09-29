<template>
	<ion-modal
		:is-open="isOpen"
		:backdrop-dismiss="false"
		class="photo-sheet-modal"
		@didDismiss="onDismissed"
	>
		<div class="photo-sheet">
			<header class="photo-sheet-header">
				<h2 class="photo-sheet-title">{{ heading }}</h2>
				<p
					v-if="step === 'intro' && mode === 'reminder' && content.deadline"
					class="photo-sheet-deadline"
					:class="{ 'is-overdue': content.overdue }"
				>
					{{ content.deadline }}
				</p>
			</header>

			<div class="photo-sheet-body">
				<div class="photo-sheet-inner">
					<template v-if="step === 'intro'">
						<div class="photo-sheet-avatar" aria-hidden="true">
							<img v-if="currentPhoto" :src="currentPhoto" alt="" />
							<Icon v-else icon="lucide-circle-user-round" class="h-12 w-12" />
						</div>
						<p class="photo-sheet-lead">
							{{ mode === "reminder" ? content.lead : t("changeLead") }}
						</p>
						<section
							v-for="section in sections"
							:key="section.id"
							class="photo-sheet-section"
							:class="`is-${section.id}`"
						>
							<h3>{{ section.title }}</h3>
							<ul>
								<li v-for="item in section.items" :key="item">{{ item }}</li>
							</ul>
						</section>
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
					<button type="button" class="photo-sheet-button is-primary" @click="pick('camera')">
						<Icon icon="lucide-camera" class="h-5 w-5" />
						{{ t("takePhoto") }}
					</button>
					<button type="button" class="photo-sheet-button is-secondary" @click="pick('library')">
						<Icon icon="lucide-image" class="h-5 w-5" />
						{{ t("choosePhoto") }}
					</button>
					<button type="button" class="photo-sheet-link" @click="close(dismissEvent)">
						{{ mode === "reminder" ? t("later") : t("cancel") }}
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
import { computed, onBeforeUnmount, ref } from "vue"
import { IonModal } from "@ionic/vue"
import { Icon } from "frappe-ui"

import ProfilePhotoEditor from "@/components/profile/ProfilePhotoEditor.vue"
import { getReminderContent, pickPhotoCopy, uploadProfilePhoto } from "@/utils/profilePhoto"

const props = defineProps({
	isOpen: { type: Boolean, default: false },
	// reminder：带用途和承诺的强提醒；change：个人页里换头像
	mode: { type: String, default: "reminder" },
	status: { type: Object, default: null },
	currentPhoto: { type: String, default: "" },
	lang: { type: String, default: "zh" },
})

const emit = defineEmits(["snooze", "cancel", "uploaded"])

const step = ref("intro")
const sourceUrl = ref("")
const editorReady = ref(false)
const uploading = ref(false)
const errorMessage = ref("")
const editorRef = ref(null)
const cameraInput = ref(null)
const libraryInput = ref(null)
let closedByUs = false

const t = (key) => pickPhotoCopy(key, props.lang)
const content = computed(() => getReminderContent(props.status, props.lang))
const sections = computed(() =>
	props.mode === "reminder"
		? content.value.sections
		: content.value.sections.filter((section) => section.id === "rules")
)
const heading = computed(() => {
	if (step.value === "edit") return t("editTitle")
	return props.mode === "reminder" ? content.value.title : t("changeTitle")
})
const dismissEvent = computed(() => (props.mode === "reminder" ? "snooze" : "cancel"))

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
		const blob = await editorRef.value.exportBlob()
		const photo = await uploadProfilePhoto(blob)
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
	closedByUs = true
	emit(event)
	reset()
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
	editorReady.value = false
}

function reset() {
	releaseSource()
	errorMessage.value = ""
	uploading.value = false
	step.value = "intro"
}

onBeforeUnmount(releaseSource)
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
	font-size: 20px;
	font-weight: 900;
	line-height: 1.3;
}

.photo-sheet-deadline {
	display: inline-block;
	margin-top: 8px;
	padding: 4px 12px;
	border-radius: 999px;
	color: var(--h-tab-active);
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	font-size: 13px;
	font-weight: 700;
}

.photo-sheet-deadline.is-overdue {
	color: var(--h-summary-warn-fg);
	background: var(--h-summary-warn-bg);
	border-color: var(--h-summary-warn-bd);
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
	width: 88px;
	height: 88px;
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
	max-width: 360px;
	color: var(--h-fg-secondary);
	font-size: 14px;
	line-height: 1.6;
	text-align: center;
}

.photo-sheet-section {
	width: min(100%, 420px);
	padding: 14px 16px;
	background: var(--h-bg-card);
	border: 1px solid var(--h-bd-default);
	border-radius: 16px;
}

.photo-sheet-section h3 {
	margin-bottom: 6px;
	font-size: 15px;
	font-weight: 800;
}

.photo-sheet-section ul {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding-left: 18px;
	list-style: disc;
	color: var(--h-fg-secondary);
	font-size: 13.5px;
	line-height: 1.6;
}

.photo-sheet-section.is-promise {
	background: var(--h-bg-card-inner);
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
