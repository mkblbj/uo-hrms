<template>
	<section class="hero-card">
		<div class="hero-top">
			<div class="hero-text">
				<p class="hero-kicker">
					{{ dateLabel }}<span v-if="weatherText"> · {{ weatherText }}</span>
				</p>
				<h2 class="hero-title">{{ greeting }}{{ employeeName ? `，${employeeName}` : "" }}</h2>
			</div>
		</div>

		<div
			v-if="shiftProgress"
			class="hero-progress"
			:class="{ 'is-overtime': shiftProgress.tone === 'overtime' }"
		>
			<div class="hero-progress-copy">
				<div>
					<span>{{ t("progressTitle") }}</span>
					<strong>{{ shiftProgress.statusLabel }}</strong>
				</div>
				<div class="hero-progress-value">
					<span>{{ shiftProgress.rangeLabel }}</span>
					<strong>{{ displayedWorkedLabel }}</strong>
				</div>
			</div>
			<div class="hero-progress-track" aria-hidden="true">
				<span :style="{ width: `${displayedProgress}%` }"></span>
			</div>
		</div>

		<div class="hero-heatmap">
			<div class="hero-heatmap-header">
				<div>
					<div class="hero-heatmap-title">{{ t("heatmapTitle") }}</div>
					<div class="hero-heatmap-subtitle">{{ t("heatmapSubtitle") }}</div>
				</div>
				<div class="hero-heatmap-legend" aria-hidden="true">
					<span>{{ t("less") }}</span>
					<i style="background: #bbf7d0"></i>
					<i style="background: #86efac"></i>
					<i style="background: #4ade80"></i>
					<i style="background: #16a34a"></i>
					<i style="background: #166534"></i>
					<span>{{ t("more") }}</span>
				</div>
			</div>

			<div v-if="attendanceResource.loading" class="hero-heatmap-state">{{ t("loading") }}</div>
			<div v-else-if="attendanceResource.error" class="hero-heatmap-state">{{ t("error") }}</div>
			<div v-else class="hero-heatmap-calendar">
				<div class="hero-heatmap-month-spacer" aria-hidden="true"></div>
				<div class="hero-heatmap-months" aria-hidden="true">
					<span v-for="marker in monthMarkers" :key="marker.key">{{ marker.label }}</span>
				</div>
				<div class="hero-heatmap-weekdays" aria-hidden="true">
					<span v-for="day in weekdayLabels" :key="day">{{ day }}</span>
				</div>
				<div class="hero-heatmap-grid">
					<span
						v-for="(cell, idx) in heatmapCells"
						:key="cell.date"
						class="hero-heatmap-cell"
						:class="{ 'is-today': cell.isToday, 'is-future': cell.isFuture }"
						:style="{ backgroundColor: cell.color, '--cell-index': idx }"
						:title="cellLabel(cell)"
						:aria-label="cellLabel(cell)"
					></span>
				</div>
			</div>
		</div>

		<div class="hero-mini-stats" :aria-busy="statsLoading">
			<div v-for="item in miniStats" :key="item.key" class="hero-mini-stat">
				<span>{{ item.label }}</span>
				<strong
					>{{ item.value }}<small>{{ item.unit }}</small></strong
				>
			</div>
		</div>
	</section>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue"

import { buildHeatmapMonthMarkers, buildRecentWeekdayHeatmap } from "@/utils/homeHeatmap"
import { buildShiftProgress } from "@/utils/homeShiftProgress"
import { formatCountUp, runCountUp } from "@/utils/homeCountUp"

const props = defineProps({
	employeeName: { type: String, default: "" },
	greeting: { type: String, required: true },
	dateLabel: { type: String, required: true },
	weatherText: { type: String, default: "" },
	workStatus: { type: Object, default: null },
	stats: { type: Object, default: null },
	statsLoading: { type: Boolean, default: false },
	lang: { type: String, default: "zh" },
	today: { type: [String, Date], default: () => new Date() },
	introPlay: { type: Boolean, default: false },
})

const copy = {
	progressTitle: { zh: "今日进度", ja: "本日の進捗", en: "Today Progress" },
	heatmapTitle: { zh: "考勤热力", ja: "勤怠ヒートマップ", en: "Attendance Heatmap" },
	heatmapSubtitle: {
		zh: "近 13 周 · 全周显示",
		ja: "直近 13 週 · 全曜日",
		en: "Last 13 weeks · full week",
	},
	loading: { zh: "加载考勤记录...", ja: "勤怠記録を読み込み中...", en: "Loading attendance..." },
	error: {
		zh: "暂时无法加载考勤记录",
		ja: "勤怠記録を読み込めません",
		en: "Unable to load attendance",
	},
	less: { zh: "少", ja: "少", en: "Less" },
	more: { zh: "多", ja: "多", en: "More" },
	hours: { zh: "小时", ja: "時間", en: "hours" },
	noRecord: { zh: "无记录", ja: "記録なし", en: "No record" },
	monthHours: { zh: "本月工时", ja: "今月時間", en: "Month Hours" },
	monthDays: { zh: "本月出勤", ja: "今月出勤", en: "Month Days" },
	avgDay: { zh: "日均", ja: "日平均", en: "Avg / Day" },
	unitHours: { zh: "h", ja: "h", en: "h" },
	unitDays: { zh: "天", ja: "日", en: "d" },
}

const weekdayMap = {
	zh: ["一", "二", "三", "四", "五", "六", "日"],
	ja: ["月", "火", "水", "木", "金", "土", "日"],
	en: ["M", "T", "W", "T", "F", "S", "S"],
}

const attendanceResource = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: false,
	cache: false,
})
const scheduleResource = createResource({
	url: "work_roster.api.schedule.get_home_schedule_summary",
	auto: false,
	cache: false,
})
const currentTime = ref(new Date())
let progressTimer = null

function t(key) {
	return copy[key]?.[props.lang] || copy[key]?.zh || key
}

function toDate(value) {
	const date = value instanceof Date ? new Date(value) : new Date(`${value}T00:00:00`)
	date.setHours(0, 0, 0, 0)
	return date
}

function toDateString(date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
		date.getDate()
	).padStart(2, "0")}`
}

function getAttendanceRange() {
	const today = toDate(props.today)
	const weekday = today.getDay() || 7
	const monday = new Date(today)
	monday.setDate(today.getDate() + 1 - weekday)
	const fromDate = new Date(monday)
	fromDate.setDate(monday.getDate() - 12 * 7)
	const sunday = new Date(monday)
	sunday.setDate(monday.getDate() + 6)

	return {
		from_date: toDateString(fromDate),
		to_date: toDateString(sunday),
	}
}

function formatNumber(value, digits = 0) {
	const numeric = Number(value || 0)
	if (!Number.isFinite(numeric)) return "0"
	return Number.isInteger(numeric) && digits === 0
		? numeric.toLocaleString()
		: numeric.toFixed(digits)
}

function reloadAttendance() {
	return attendanceResource.fetch(getAttendanceRange())
}

function reloadSchedule() {
	return scheduleResource.fetch()
}

const weekdayLabels = computed(() => weekdayMap[props.lang] || weekdayMap.zh)
const todaySchedule = computed(() => scheduleResource.data?.today_entry || null)
const shiftProgress = computed(() =>
	buildShiftProgress({
		schedule: todaySchedule.value,
		stats: props.stats || {},
		workStatus: props.workStatus,
		now: currentTime.value,
		lang: props.lang,
	})
)
const displayedProgress = ref(0)
const initialAnimationFired = ref(false)
const displayedMonthHours = ref(0)
const displayedMonthDays = ref(0)
const displayedAvg = ref(0)
const displayedWorkedHours = ref(0)
let countUpStarted = false
const prefersReducedMotion =
	typeof window !== "undefined" && typeof window.matchMedia === "function"
		? window.matchMedia("(prefers-reduced-motion: reduce)").matches
		: false

const heatmapCells = computed(() =>
	buildRecentWeekdayHeatmap({
		events: attendanceResource.data || {},
		today: props.today,
	})
)
const monthMarkers = computed(() =>
	buildHeatmapMonthMarkers({
		cells: heatmapCells.value,
		lang: props.lang,
	})
)
const miniStats = computed(() => {
	return [
		{
			key: "month_hours",
			label: t("monthHours"),
			value: props.statsLoading ? "--" : formatCountUp(displayedMonthHours.value, 1),
			unit: t("unitHours"),
		},
		{
			key: "month_present",
			label: t("monthDays"),
			value: props.statsLoading ? "--" : formatCountUp(displayedMonthDays.value, 0),
			unit: t("unitDays"),
		},
		{
			key: "avg_day",
			label: t("avgDay"),
			value: props.statsLoading ? "--" : formatCountUp(displayedAvg.value, 1),
			unit: t("unitHours"),
		},
	]
})

const displayedWorkedLabel = computed(() => {
	const sp = shiftProgress.value
	if (!sp) return ""
	if (sp.hasOvertime) return sp.workedLabel
	const shift = sp.shiftHours || 0
	return `${formatCountUp(displayedWorkedHours.value, 1)} / ${shift.toFixed(1)}h`
})

function startCountUpsOnce() {
	if (countUpStarted) return
	if (!props.stats || props.statsLoading) return
	countUpStarted = true

	const monthHoursTarget = Number(props.stats?.month_hours || 0)
	const monthDaysTarget = Number(props.stats?.month_present || 0)
	const avgTarget = monthDaysTarget > 0 ? monthHoursTarget / monthDaysTarget : 0
	const workedTarget = Number(shiftProgress.value?.workedHours || 0)

	if (prefersReducedMotion || !props.introPlay) {
		displayedMonthHours.value = monthHoursTarget
		displayedMonthDays.value = monthDaysTarget
		displayedAvg.value = avgTarget
		displayedWorkedHours.value = workedTarget
		return
	}

	runCountUp({
		target: monthHoursTarget,
		duration: 1000,
		onUpdate: (v) => (displayedMonthHours.value = v),
	})
	runCountUp({
		target: monthDaysTarget,
		duration: 1000,
		onUpdate: (v) => (displayedMonthDays.value = v),
	})
	runCountUp({
		target: avgTarget,
		duration: 1000,
		onUpdate: (v) => (displayedAvg.value = v),
	})
	runCountUp({
		target: workedTarget,
		duration: 1200,
		onUpdate: (v) => (displayedWorkedHours.value = v),
	})
}

function cellLabel(cell) {
	const status = cell.event?.attendance || t("noRecord")
	const hours = cell.event?.working_hours
	const hoursText = hours ? `, ${hours} ${t("hours")}` : ""
	return `${cell.date}: ${status}${hoursText}`
}

onMounted(() => {
	reloadAttendance()
	reloadSchedule()
	progressTimer = setInterval(() => {
		currentTime.value = new Date()
	}, 60 * 1000)

	if (prefersReducedMotion) {
		displayedProgress.value = shiftProgress.value?.percent || 0
		initialAnimationFired.value = true
		return
	}
	requestAnimationFrame(() => {
		requestAnimationFrame(() => {
			displayedProgress.value = shiftProgress.value?.percent || 0
			initialAnimationFired.value = true
		})
	})
})

onBeforeUnmount(() => {
	if (progressTimer) {
		clearInterval(progressTimer)
		progressTimer = null
	}
})

watch(
	() => shiftProgress.value?.percent ?? 0,
	(next) => {
		// After the initial mount animation has fired, keep displayed in sync.
		// If the initial animation hasn't fired yet, do nothing — onMounted will set it.
		if (!initialAnimationFired.value && !prefersReducedMotion) return
		displayedProgress.value = next
	},
)

watch(
	[() => props.stats, () => props.statsLoading, () => shiftProgress.value?.workedHours ?? 0],
	() => {
		if (countUpStarted) {
			const monthHours = Number(props.stats?.month_hours || 0)
			const monthDays = Number(props.stats?.month_present || 0)
			displayedMonthHours.value = monthHours
			displayedMonthDays.value = monthDays
			displayedAvg.value = monthDays > 0 ? monthHours / monthDays : 0
			displayedWorkedHours.value = Number(shiftProgress.value?.workedHours || 0)
			return
		}
		startCountUpsOnce()
	},
	{ immediate: true },
)

defineExpose({ reloadAttendance, reloadSchedule })
</script>

<style scoped>
.hero-card {
	display: flex;
	flex-direction: column;
	gap: 16px;
	border-radius: 22px;
	background: #ffffff;
	padding: 18px;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 14px 28px rgba(15, 23, 42, 0.06);
}

.hero-top {
	display: flex;
	align-items: flex-start;
}

.hero-text {
	min-width: 0;
}

.hero-kicker {
	margin: 0 0 6px;
	font-size: 12px;
	line-height: 1.35;
	font-weight: 700;
	color: #64748b;
}

.hero-title {
	margin: 0;
	font-size: 24px;
	line-height: 1.18;
	font-weight: 900;
	letter-spacing: 0;
	color: #0a0a0a;
}

.hero-progress {
	display: grid;
	gap: 8px;
	border-radius: 14px;
	background: #faf8f2;
	padding: 12px;
}

.hero-progress-copy {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 12px;
}

.hero-progress-copy span {
	display: block;
	font-size: 11px;
	line-height: 1.2;
	font-weight: 800;
	color: #64748b;
}

.hero-progress-copy strong {
	display: block;
	margin-top: 3px;
	font-size: 13px;
	line-height: 1.2;
	font-weight: 900;
	color: #0a0a0a;
}

.hero-progress-value {
	min-width: 0;
	text-align: right;
}

.hero-progress-track {
	height: 8px;
	overflow: hidden;
	border-radius: 999px;
	background: #e3dfd4;
}

.hero-progress-track span {
	display: block;
	height: 100%;
	border-radius: inherit;
	background: linear-gradient(90deg, #86efac 0%, #16a34a 100%);
	transition: width 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}

.hero-progress.is-overtime {
	background: #fff7ed;
}

.hero-progress.is-overtime .hero-progress-copy strong {
	color: #9a3412;
}

.hero-progress.is-overtime .hero-progress-track {
	background: #fed7aa;
}

.hero-progress.is-overtime .hero-progress-track span {
	background: linear-gradient(90deg, #fbbf24 0%, #f97316 100%);
}

.hero-heatmap {
	display: grid;
	gap: 12px;
}

.hero-heatmap-header {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 12px;
}

.hero-heatmap-title {
	font-size: 15px;
	line-height: 1.25;
	font-weight: 900;
	color: #0a0a0a;
}

.hero-heatmap-subtitle {
	margin-top: 3px;
	font-size: 11px;
	font-weight: 700;
	color: #64748b;
}

.hero-heatmap-legend {
	display: flex;
	align-items: center;
	gap: 4px;
	font-size: 10px;
	font-weight: 700;
	color: #64748b;
}

.hero-heatmap-legend i {
	width: 9px;
	height: 9px;
	border-radius: 2px;
}

.hero-heatmap-state {
	border-radius: 12px;
	background: #faf8f2;
	padding: 18px 12px;
	text-align: center;
	font-size: 12px;
	font-weight: 700;
	color: #64748b;
}

.hero-heatmap-calendar {
	display: grid;
	grid-template-columns: 18px minmax(0, 1fr);
	grid-template-rows: auto auto;
	column-gap: 8px;
	row-gap: 5px;
}

.hero-heatmap-month-spacer {
	grid-column: 1;
	grid-row: 1;
}

.hero-heatmap-months {
	grid-column: 2;
	grid-row: 1;
	display: grid;
	grid-template-columns: repeat(13, minmax(0, 1fr));
	gap: 3px;
	min-height: 14px;
	font-size: 10px;
	font-weight: 800;
	color: #64748b;
}

.hero-heatmap-months span {
	overflow: hidden;
	white-space: nowrap;
}

.hero-heatmap-weekdays {
	grid-column: 1;
	grid-row: 2;
	display: grid;
	grid-template-rows: repeat(7, minmax(0, 1fr));
	gap: 3px;
	font-size: 10px;
	font-weight: 800;
	color: #64748b;
}

.hero-heatmap-weekdays span {
	display: flex;
	align-items: center;
	justify-content: flex-end;
}

.hero-heatmap-grid {
	grid-column: 2;
	grid-row: 2;
	display: grid;
	grid-template-columns: repeat(13, minmax(0, 1fr));
	grid-template-rows: repeat(7, minmax(0, 1fr));
	grid-auto-flow: column;
	gap: 3px;
}

.hero-heatmap-cell {
	aspect-ratio: 1;
	min-width: 0;
	border-radius: 5px;
	outline: 1px solid rgba(255, 255, 255, 0.66);
}

.hero-heatmap-cell.is-today {
	box-shadow: 0 0 0 2px #16a34a, 0 0 8px rgba(22, 163, 74, 0.35);
}

@media (prefers-reduced-motion: no-preference) {
	.hero-heatmap-cell.is-today {
		animation: today-pulse 2800ms ease-in-out infinite;
	}
}

@keyframes today-pulse {
	0%, 100% {
		box-shadow: 0 0 0 2px #16a34a, 0 0 8px rgba(22, 163, 74, 0.35);
	}
	50% {
		box-shadow: 0 0 0 2px #16a34a, 0 0 14px rgba(22, 163, 74, 0.55);
	}
}

@media (prefers-reduced-motion: no-preference) {
	.intro-play .hero-heatmap-cell.is-today {
		animation:
			hm-cell-in 560ms cubic-bezier(0.22, 1, 0.36, 1) forwards,
			today-ring-in 2400ms ease-out forwards,
			today-pulse 2800ms ease-in-out infinite;
		animation-delay:
			calc(var(--cell-index, 0) * 3.5ms),
			calc(var(--cell-index, 0) * 3.5ms),
			calc(var(--cell-index, 0) * 3.5ms + 2400ms);
	}
}

@keyframes today-ring-in {
	from {
		box-shadow: 0 0 0 0 rgba(22, 163, 74, 0), 0 0 0 rgba(22, 163, 74, 0);
	}
	to {
		box-shadow: 0 0 0 2px #16a34a, 0 0 8px rgba(22, 163, 74, 0.35);
	}
}

.hero-heatmap-cell.is-future {
	opacity: 0.74;
}

@media (prefers-reduced-motion: no-preference) {
	.intro-play .hero-heatmap-cell {
		opacity: 0;
		transform: translateY(8px);
		animation: hm-cell-in 560ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
		animation-delay: calc(var(--cell-index, 0) * 3.5ms);
	}
}

@keyframes hm-cell-in {
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

.hero-mini-stats {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 8px;
}

.hero-mini-stat {
	min-width: 0;
	border: 1px solid #ede9dd;
	border-radius: 14px;
	background: #faf8f2;
	padding: 10px;
}

.hero-mini-stat span {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 10px;
	font-weight: 800;
	color: #64748b;
}

.hero-mini-stat strong {
	display: block;
	margin-top: 4px;
	font-size: 18px;
	line-height: 1;
	font-weight: 900;
	color: #0a0a0a;
	font-variant-numeric: tabular-nums;
}

.hero-mini-stat small {
	margin-left: 2px;
	font-size: 10px;
	font-weight: 800;
	color: #64748b;
}

@media (max-width: 359px) {
	.hero-card {
		padding: 16px;
	}

	.hero-title {
		font-size: 22px;
	}

	.hero-heatmap-legend {
		display: none;
	}
}

@media (prefers-reduced-motion: reduce) {
	.hero-progress-track span {
		transition: none !important;
	}
}

@media (prefers-reduced-motion: no-preference) {
	.hero-heatmap-state {
		animation: hm-state-pulse 1.4s ease-in-out infinite;
	}
}

@keyframes hm-state-pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.55; }
}
</style>
