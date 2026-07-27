<template>
	<Teleport to="body">
		<div v-if="day" class="roster-sheet-layer" @click.self="emit('close')">
			<section
				ref="panel"
				class="roster-day-sheet"
				role="dialog"
				aria-modal="true"
				:aria-label="day.ariaLabel"
				tabindex="-1"
				@pointerdown="startDrag"
				@pointerup="finishDrag"
				@pointercancel="cancelDrag"
			>
				<div class="sheet-handle" aria-hidden="true"></div>
				<button
					type="button"
					class="sheet-close"
					:aria-label="labels.close"
					@click="emit('close')"
				>
					×
				</button>

				<header class="sheet-header">
					<div>
						<p v-if="day.isToday" class="today-label">
							{{ labels.pageTitle }}
						</p>
						<h2>{{ day.dateStr }}</h2>
					</div>
					<div v-if="day.event || day.holidayName" class="day-notes">
						<span v-if="day.event">{{ day.event.title }}</span>
						<span v-if="day.holidayName">{{ day.holidayName }}</span>
					</div>
				</header>

				<div class="sheet-content">
					<template v-if="scope === 'mine'">
						<article v-if="day.data?.my_shift" class="personal-shift">
							<div>
								<span>{{ labels.shiftLabel }}</span>
								<strong>
									{{ day.data.my_shift.shift_label || labels.customTime }}
								</strong>
							</div>
							<div>
								<span>{{ labels.scheduledTime }}</span>
								<strong>
									{{ day.data.my_shift.scheduled_time || labels.customTime }}
								</strong>
							</div>
						</article>
						<p v-else class="empty-day">{{ labels.emptyDay }}</p>
					</template>

					<template v-else>
						<div class="department-summary">
							<strong>
								{{ labels.scheduledPeople.replace("{count}", day.data?.actual_count ?? 0) }}
							</strong>
							<strong
								v-if="departmentCategory === 'Production' && day.data?.equivalent_count != null"
							>
								{{
									labels.equivalentPeople.replace(
										"{count}",
										Number(day.data.equivalent_count).toFixed(1)
									)
								}}
							</strong>
						</div>

						<ul v-if="day.data?.employees?.length" class="employee-list">
							<li v-for="employee in day.data.employees" :key="employee.employee">
								<strong>{{ employee.employee_name }}</strong>
								<span>
									{{ employee.shift_label || labels.customTime }}
								</span>
								<time>
									{{ employee.scheduled_time || labels.customTime }}
								</time>
							</li>
						</ul>
						<p v-else class="empty-day">{{ labels.emptyDay }}</p>
					</template>
				</div>
			</section>
		</div>
	</Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"

import { shouldCloseRosterSheet } from "@/utils/rosterCalendar"

const props = defineProps({
	day: {
		type: Object,
		default: null,
	},
	scope: {
		type: String,
		required: true,
	},
	departmentCategory: {
		type: String,
		default: "",
	},
	labels: {
		type: Object,
		required: true,
	},
})

const emit = defineEmits(["close"])
const panel = ref(null)
let dragStartY = null
let previousBodyOverflow = ""
let bodyLocked = false

function startDrag(event) {
	dragStartY = event.clientY
}

function finishDrag(event) {
	if (dragStartY != null && shouldCloseRosterSheet(event.clientY - dragStartY)) {
		emit("close")
	}
	dragStartY = null
}

function cancelDrag() {
	dragStartY = null
}

function handleKeydown(event) {
	if (props.day && event.key === "Escape") {
		emit("close")
	}
}

function handleBackButton(event) {
	if (!props.day) return
	event.detail?.register?.(100, () => emit("close"))
}

function unlockBody() {
	if (!bodyLocked) return
	document.body.style.overflow = previousBodyOverflow
	bodyLocked = false
}

watch(
	() => props.day,
	async (day) => {
		if (!day) {
			unlockBody()
			return
		}
		if (!bodyLocked) {
			previousBodyOverflow = document.body.style.overflow
			document.body.style.overflow = "hidden"
			bodyLocked = true
		}
		await nextTick()
		panel.value?.focus()
	}
)

onMounted(() => {
	window.addEventListener("keydown", handleKeydown)
	document.addEventListener("ionBackButton", handleBackButton)
})

onBeforeUnmount(() => {
	unlockBody()
	window.removeEventListener("keydown", handleKeydown)
	document.removeEventListener("ionBackButton", handleBackButton)
})
</script>

<style scoped>
.roster-sheet-layer {
	position: fixed;
	z-index: 1000;
	inset: 0;
	display: flex;
	align-items: flex-end;
	justify-content: center;
	padding: 0;
	background: rgba(15, 23, 42, 0.46);
	overscroll-behavior: contain;
}

.roster-day-sheet {
	position: relative;
	width: min(100%, 480px);
	max-height: min(78dvh, 680px);
	padding: 12px 16px calc(16px + env(safe-area-inset-bottom));
	color: var(--h-fg-primary, #0a0a0a);
	background: var(--h-bg-card, #ffffff);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-bottom: 0;
	border-radius: 22px 22px 0 0;
	box-shadow: 0 -12px 40px rgba(15, 23, 42, 0.2);
}

.roster-day-sheet:focus {
	outline: none;
}

.sheet-handle {
	width: 40px;
	height: 4px;
	margin: 0 auto 10px;
	background: var(--h-bd-default, #e3dfd4);
	border-radius: 999px;
}

.sheet-close {
	position: absolute;
	top: 12px;
	right: 12px;
	display: grid;
	width: 40px;
	height: 40px;
	place-items: center;
	padding: 0;
	color: var(--h-fg-secondary, #64748b);
	font-size: 24px;
	line-height: 1;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 50%;
}

.sheet-close:focus-visible {
	outline: 2px solid var(--h-tab-active, #2563eb);
	outline-offset: 2px;
}

.sheet-header {
	display: grid;
	gap: 8px;
	padding: 2px 48px 14px 2px;
	border-bottom: 1px solid var(--h-bd-subtle, #ede9dd);
}

.sheet-header h2,
.sheet-header p {
	margin: 0;
}

.sheet-header h2 {
	font-size: 21px;
}

.today-label {
	margin-bottom: 2px !important;
	color: var(--h-tab-active, #2563eb);
	font-size: 11px;
	font-weight: 700;
}

.day-notes {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
}

.day-notes span {
	padding: 4px 8px;
	color: var(--h-summary-warn-fg, #92400e);
	font-size: 11px;
	font-weight: 650;
	background: var(--h-summary-warn-bg, #fffbeb);
	border: 1px solid var(--h-summary-warn-bd, #fde68a);
	border-radius: 999px;
}

.sheet-content {
	max-height: calc(min(78dvh, 680px) - 100px);
	padding-top: 14px;
	overflow-y: auto;
	overscroll-behavior: contain;
}

.personal-shift {
	display: grid;
	gap: 10px;
}

.personal-shift div {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	padding: 12px;
	background: var(--h-bg-card-inner, #faf8f2);
	border-radius: 12px;
}

.personal-shift span,
.employee-list span,
.employee-list time {
	color: var(--h-fg-secondary, #64748b);
	font-size: 12px;
}

.department-summary {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 12px;
}

.department-summary strong {
	padding: 6px 9px;
	color: var(--h-fg-primary, #0a0a0a);
	font-size: 12px;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 999px;
}

.employee-list {
	display: grid;
	gap: 6px;
	margin: 0;
	padding: 0;
	list-style: none;
}

.employee-list li {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 3px 10px;
	padding: 10px 12px;
	background: var(--h-bg-card-inner, #faf8f2);
	border: 1px solid var(--h-bd-subtle, #ede9dd);
	border-radius: 12px;
}

.employee-list strong {
	overflow: hidden;
	font-size: 14px;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.employee-list span {
	grid-row: 2;
}

.employee-list time {
	grid-row: 1 / span 2;
	grid-column: 2;
	align-self: center;
	font-variant-numeric: tabular-nums;
}

.empty-day {
	margin: 0;
	padding: 24px 12px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 14px;
	text-align: center;
	background: var(--h-bg-card-inner, #faf8f2);
	border-radius: 12px;
}
</style>
