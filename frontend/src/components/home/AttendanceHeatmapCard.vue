<template>
	<section class="attendance-heatmap-card">
		<div class="heatmap-header">
			<h3>{{ t("title") }}</h3>
			<span>{{ t("period") }}</span>
		</div>

		<div v-if="attendanceResource.loading" class="heatmap-loading">{{ t("loading") }}</div>
		<div v-else-if="attendanceResource.error" class="heatmap-empty">{{ t("error") }}</div>
		<div v-else class="heatmap-body">
			<div class="heatmap-calendar">
				<div class="heatmap-month-spacer" aria-hidden="true"></div>
				<div class="heatmap-months" aria-hidden="true">
					<span v-for="marker in monthMarkers" :key="marker.key">{{ marker.label }}</span>
				</div>
				<div class="heatmap-weekdays" aria-hidden="true">
					<span v-for="day in weekdayLabels" :key="day">{{ day }}</span>
				</div>
				<div class="heatmap-grid">
					<span
						v-for="cell in heatmapCells"
						:key="cell.date"
						class="heatmap-cell"
						:style="{ backgroundColor: cell.color }"
						:title="cellLabel(cell)"
						:aria-label="cellLabel(cell)"
					></span>
				</div>
			</div>
		</div>

		<div class="heatmap-legend" aria-hidden="true">
			<span>{{ t("noAttendance") }}</span>
			<span style="background: #fde68a"></span>
			<span>{{ t("less") }}</span>
			<span style="background: #bbf7d0"></span>
			<span style="background: #86efac"></span>
			<span style="background: #4ade80"></span>
			<span style="background: #16a34a"></span>
			<span style="background: #166534"></span>
			<span>{{ t("more") }}</span>
		</div>
	</section>
</template>

<script setup>
import { computed, onMounted } from "vue"
import { createResource } from "frappe-ui"

import { buildHeatmapMonthMarkers, buildRecentWeekdayHeatmap } from "@/utils/homeHeatmap"

const props = defineProps({
	lang: {
		type: String,
		default: "zh",
	},
	today: {
		type: [String, Date],
		default: () => new Date(),
	},
})

const copy = {
	title: { zh: "考勤记录", ja: "勤怠記録", en: "Attendance" },
	period: { zh: "近 13 周", ja: "直近 13 週", en: "Last 13 weeks" },
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	error: { zh: "暂时无法加载考勤记录", ja: "勤怠記録を読み込めません", en: "Unable to load attendance" },
	less: { zh: "少", ja: "少", en: "Less" },
	more: { zh: "多", ja: "多", en: "More" },
	noAttendance: { zh: "无考勤", ja: "勤怠なし", en: "No attendance" },
	hours: { zh: "小时", ja: "時間", en: "hours" },
	noRecord: { zh: "无记录", ja: "記録なし", en: "No record" },
}

const weekdayMap = {
	zh: ["一", "二", "三", "四", "五", "六", "日"],
	ja: ["月", "火", "水", "木", "金", "土", "日"],
	en: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
}

const attendanceResource = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: false,
	cache: false,
})

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

function getRange() {
	const today = toDate(props.today)
	const day = today.getDay() || 7
	const monday = new Date(today)
	monday.setDate(today.getDate() + 1 - day)
	const fromDate = new Date(monday)
	fromDate.setDate(monday.getDate() - 12 * 7)
	const sunday = new Date(monday)
	sunday.setDate(monday.getDate() + 6)

	return {
		from_date: toDateString(fromDate),
		to_date: toDateString(sunday),
	}
}

function loadAttendance() {
	attendanceResource.fetch(getRange())
}

const weekdayLabels = computed(() => weekdayMap[props.lang] || weekdayMap.zh)
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

function cellLabel(cell) {
	const status = cell.event?.attendance || t("noRecord")
	const hours = cell.event?.working_hours
	const hoursText = hours ? `, ${hours} ${t("hours")}` : ""
	return `${cell.date}: ${status}${hoursText}`
}

onMounted(loadAttendance)
</script>

<style scoped>
.attendance-heatmap-card {
	border-radius: 16px;
	background: #ffffff;
	padding: 16px;
	box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.02);
}

.heatmap-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 12px;
}

.heatmap-header h3 {
	margin: 0;
	font-size: 15px;
	font-weight: 800;
	color: #0f172a;
}

.heatmap-header span,
.heatmap-loading,
.heatmap-empty {
	font-size: 12px;
	font-weight: 600;
	color: #64748b;
}

.heatmap-body {
	width: 100%;
}

.heatmap-calendar {
	display: grid;
	grid-template-columns: 18px minmax(0, 1fr);
	grid-template-rows: auto auto;
	column-gap: 6px;
	row-gap: 4px;
}

.heatmap-month-spacer {
	grid-column: 1;
	grid-row: 1;
}

.heatmap-months {
	grid-column: 2;
	grid-row: 1;
	display: grid;
	grid-template-columns: repeat(13, minmax(0, 1fr));
	gap: 3px;
	min-height: 14px;
	font-size: 10px;
	font-weight: 700;
	color: #64748b;
}

.heatmap-months span {
	overflow: hidden;
	white-space: nowrap;
}

.heatmap-weekdays {
	grid-column: 1;
	grid-row: 2;
	display: grid;
	grid-template-rows: repeat(7, 1fr);
	gap: 3px;
	font-size: 10px;
	color: #64748b;
}

.heatmap-weekdays span {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	min-height: 20px;
}

.heatmap-grid {
	grid-column: 2;
	grid-row: 2;
	display: grid;
	grid-template-columns: repeat(13, minmax(0, 1fr));
	grid-template-rows: repeat(7, 1fr);
	grid-auto-flow: column;
	gap: 3px;
}

.heatmap-cell {
	aspect-ratio: 1;
	min-width: 0;
	border-radius: 4px;
	outline: 1px solid rgba(255, 255, 255, 0.6);
}

.heatmap-legend {
	display: flex;
	align-items: center;
	justify-content: flex-end;
	gap: 4px;
	margin-top: 10px;
	font-size: 10px;
	color: #64748b;
}

.heatmap-legend span:nth-child(2),
.heatmap-legend span:nth-child(n + 4):nth-child(-n + 8) {
	width: 12px;
	height: 12px;
	border-radius: 3px;
}
</style>
