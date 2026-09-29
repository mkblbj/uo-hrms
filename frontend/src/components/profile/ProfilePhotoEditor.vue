<template>
	<div class="photo-editor">
		<div
			ref="viewportRef"
			class="photo-editor-viewport"
			@pointerdown="onPointerDown"
			@pointermove="onPointerMove"
			@pointerup="onPointerEnd"
			@pointercancel="onPointerEnd"
			@wheel.prevent="onWheel"
		>
			<img
				v-show="natural.width"
				ref="imageRef"
				class="photo-editor-image"
				:src="src"
				:style="imageStyle"
				alt=""
				draggable="false"
				@load="onLoad"
				@error="emit('error', 'readFailed')"
			/>
			<div class="photo-editor-ring" aria-hidden="true"></div>
		</div>

		<label class="photo-editor-zoom">
			<Icon icon="lucide-zoom-out" class="h-4 w-4" />
			<input
				type="range"
				min="1"
				step="0.01"
				:max="maxZoom"
				:value="zoom"
				:disabled="maxZoom <= 1"
				:aria-label="pickPhotoCopy('zoom', lang)"
				@input="setZoom(Number($event.target.value))"
			/>
			<Icon icon="lucide-zoom-in" class="h-4 w-4" />
		</label>
		<p class="photo-editor-hint">{{ pickPhotoCopy("editHint", lang) }}</p>
	</div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { Icon } from "frappe-ui"

import {
	PHOTO_MIN_SIDE,
	clampOffset,
	cropRect,
	maxZoomFor,
	outputSizeFor,
	pickPhotoCopy,
} from "@/utils/profilePhoto"

defineProps({
	src: { type: String, required: true },
	lang: { type: String, default: "zh" },
})

const emit = defineEmits(["ready", "error"])

const viewportRef = ref(null)
const imageRef = ref(null)
const viewport = ref(280)
const natural = reactive({ width: 0, height: 0 })
const zoom = ref(1)
const offset = reactive({ x: 0, y: 0 })
const pointers = new Map()
let gesture = null
let resizeObserver = null

const maxZoom = computed(() => (natural.width ? maxZoomFor(natural.width, natural.height) : 1))
const scale = computed(() =>
	natural.width ? (viewport.value / Math.min(natural.width, natural.height)) * zoom.value : 1
)
const imageStyle = computed(() => ({
	width: `${natural.width * scale.value}px`,
	height: `${natural.height * scale.value}px`,
	transform: `translate(calc(-50% + ${offset.x}px), calc(-50% + ${offset.y}px))`,
}))

function geometry(overrides = {}) {
	return {
		width: natural.width,
		height: natural.height,
		viewport: viewport.value,
		zoom: zoom.value,
		x: offset.x,
		y: offset.y,
		...overrides,
	}
}

function limitZoom(value) {
	return Math.min(Math.max(value || 1, 1), maxZoom.value)
}

function setOffset(x, y) {
	const next = clampOffset(geometry({ x, y }))
	offset.x = next.x
	offset.y = next.y
}

// 缩放时让取景框中心看到的位置不变
function setZoom(value) {
	const next = limitZoom(value)
	const ratio = next / zoom.value
	zoom.value = next
	setOffset(offset.x * ratio, offset.y * ratio)
}

function measure() {
	viewport.value = viewportRef.value?.clientWidth || viewport.value
}

function onLoad() {
	natural.width = imageRef.value.naturalWidth
	natural.height = imageRef.value.naturalHeight
	measure()
	zoom.value = 1
	offset.x = 0
	offset.y = 0
	if (Math.min(natural.width, natural.height) < PHOTO_MIN_SIDE) {
		emit("error", "tooSmall")
		return
	}
	emit("ready")
}

function pointList() {
	return [...pointers.values()]
}

function midpoint(points) {
	return {
		x: points.reduce((sum, point) => sum + point.x, 0) / points.length,
		y: points.reduce((sum, point) => sum + point.y, 0) / points.length,
	}
}

function spread(points) {
	return points.length > 1 ? Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y) : 0
}

function startGesture() {
	const points = pointList()
	gesture = points.length
		? {
				center: midpoint(points),
				spread: spread(points),
				zoom: zoom.value,
				x: offset.x,
				y: offset.y,
		  }
		: null
}

function onPointerDown(event) {
	if (!natural.width) return
	event.currentTarget.setPointerCapture?.(event.pointerId)
	pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
	startGesture()
}

// 一根手指拖动，两根手指捏合缩放（同时也能拖）
function onPointerMove(event) {
	if (!gesture || !pointers.has(event.pointerId)) return
	pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
	const points = pointList()
	const center = midpoint(points)
	let nextZoom = gesture.zoom
	if (points.length > 1 && gesture.spread > 0) {
		nextZoom = limitZoom(gesture.zoom * (spread(points) / gesture.spread))
	}
	const ratio = nextZoom / gesture.zoom
	zoom.value = nextZoom
	setOffset(
		gesture.x * ratio + center.x - gesture.center.x,
		gesture.y * ratio + center.y - gesture.center.y
	)
}

function onPointerEnd(event) {
	pointers.delete(event.pointerId)
	startGesture()
}

function onWheel(event) {
	if (!natural.width) return
	setZoom(zoom.value * (event.deltaY < 0 ? 1.08 : 1 / 1.08))
}

function exportBlob() {
	return new Promise((resolve, reject) => {
		if (!natural.width) {
			reject(new Error("photo not ready"))
			return
		}
		const rect = cropRect(geometry())
		const size = outputSizeFor(rect.size)
		const canvas = document.createElement("canvas")
		canvas.width = size
		canvas.height = size
		const context = canvas.getContext("2d")
		context.imageSmoothingQuality = "high"
		context.fillStyle = "#ffffff"
		context.fillRect(0, 0, size, size)
		context.drawImage(imageRef.value, rect.sx, rect.sy, rect.size, rect.size, 0, 0, size, size)
		canvas.toBlob(
			(blob) => (blob ? resolve(blob) : reject(new Error("photo encode failed"))),
			"image/jpeg",
			0.9
		)
	})
}

defineExpose({ exportBlob })

onMounted(() => {
	measure()
	if (typeof ResizeObserver === "function" && viewportRef.value) {
		resizeObserver = new ResizeObserver(() => {
			const before = viewport.value
			measure()
			if (before && before !== viewport.value) {
				const ratio = viewport.value / before
				setOffset(offset.x * ratio, offset.y * ratio)
			}
		})
		resizeObserver.observe(viewportRef.value)
	}
})

onBeforeUnmount(() => {
	resizeObserver?.disconnect()
	pointers.clear()
})
</script>

<style scoped>
.photo-editor {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 16px;
	width: 100%;
}

.photo-editor-viewport {
	position: relative;
	width: min(76vw, 300px);
	aspect-ratio: 1;
	overflow: hidden;
	border-radius: 28px;
	background: #111111;
	cursor: grab;
	touch-action: none;
	user-select: none;
	-webkit-user-select: none;
}

.photo-editor-viewport:active {
	cursor: grabbing;
}

.photo-editor-image {
	position: absolute;
	top: 50%;
	left: 50%;
	max-width: none;
	pointer-events: none;
	user-select: none;
	-webkit-user-drag: none;
}

/* 圆形取景框：框外压暗，框里就是最后显示的样子 */
.photo-editor-ring {
	position: absolute;
	inset: 0;
	border: 2px solid rgba(255, 255, 255, 0.92);
	border-radius: 50%;
	box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.55);
	pointer-events: none;
}

.photo-editor-zoom {
	display: flex;
	align-items: center;
	gap: 12px;
	width: min(76vw, 300px);
	color: var(--h-fg-secondary);
}

.photo-editor-zoom input {
	flex: 1;
	accent-color: var(--h-tab-active);
}

.photo-editor-hint {
	color: var(--h-fg-secondary);
	font-size: 13px;
	line-height: 1.5;
	text-align: center;
}
</style>
