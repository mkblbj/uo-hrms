<template>
	<div class="calendar-wrapper" v-if="calendarEvents.data">
		<div class="calendar-section">
			<div class="section-title">{{ getTitle('calendar') }}</div>
			<div class="calendar-card">
				<!-- Month Change -->
				<div class="month-nav">
					<Button
						icon="chevron-left"
						variant="ghost"
						@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
					/>
					<span class="month-label">
						{{ firstOfMonth.format("YYYY年M月") }}
					</span>
					<Button
						icon="chevron-right"
						variant="ghost"
						@click="firstOfMonth = firstOfMonth.add(1, 'M')"
					/>
				</div>

				<!-- Calendar -->
				<div class="calendar-grid">
					<div v-for="day in DAYS" class="day-header">
						{{ day }}
					</div>
					<div v-for="_ in firstOfMonth.get('d')" class="day-cell" />
					<div v-for="index in firstOfMonth.endOf('M').get('D')" class="day-cell">
						<div
							class="day-circle"
							:class="getDateClasses(index)"
							@click="showDateDetail(index)"
						>
							<span
								v-if="hasShift(index)"
								class="shift-indicator"
								:class="getEventOnDate(index)?.attendance ? '' : 'shift-only'"
							/>
							<span class="day-number">{{ index }}</span>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- 月度统计卡片 -->
		<div class="stats-section">
			<div class="stats-row">
				<div class="stat-card">
					<div class="stat-icon present-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
							<polyline points="22 4 12 14.01 9 11.01"/>
						</svg>
					</div>
					<div class="stat-info">
						<div class="stat-value">{{ summary['Present'] || 0 }}<span class="stat-unit">{{ getTitle('days') }}</span></div>
						<div class="stat-label">{{ getTitle('present') }}</div>
					</div>
				</div>
				<div class="stat-card">
					<div class="stat-icon hours-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<circle cx="12" cy="12" r="10"/>
							<polyline points="12 6 12 12 16 14"/>
						</svg>
					</div>
					<div class="stat-info">
						<div class="stat-value">{{ totalHours }}<span class="stat-unit">h</span></div>
						<div class="stat-label">{{ getTitle('hours') }}</div>
					</div>
				</div>
			</div>

			<!-- 图例 -->
			<div class="legend-row">
				<div v-for="status in summaryStatuses" class="legend-item">
					<span class="legend-dot" :class="colorMap[status]" />
					<span class="legend-label">{{ __(status) }}</span>
					<span class="legend-count">{{ summary[status] || 0 }}</span>
				</div>
			</div>
		</div>
	</div>

	<!-- 日期详情弹窗 -->
	<Dialog v-model="showDetailDialog">
		<template #body-title>
			<h2 class="text-lg font-bold text-gray-800">
				{{ selectedDate ? formatDate(selectedDate) : "" }}
			</h2>
		</template>
		<template #body-content>
			<div class="space-y-3" v-if="selectedDateData">
				<!-- 考勤状态 -->
				<div v-if="selectedDateData.attendance" class="detail-item">
					<div class="detail-label">{{ __("Attendance Status") }}</div>
					<div class="detail-value" :class="getStatusClass(selectedDateData.attendance)">
						{{ __(selectedDateData.attendance) }}
					</div>
				</div>

				<!-- 签到签退记录 -->
				<div v-if="selectedDateData.in_time || selectedDateData.out_time" class="detail-item">
					<div class="detail-label">签到 / 签退</div>
					<div class="detail-value">
						<span class="text-green-600">{{ selectedDateData.in_time || "--:--" }}</span>
						<span class="mx-2 text-gray-400">→</span>
						<span class="text-red-600">{{ selectedDateData.out_time || "--:--" }}</span>
					</div>
				</div>

				<!-- 工作时长 -->
				<div v-if="selectedDateData.working_hours" class="detail-item">
					<div class="detail-label">{{ __("Working Hours") }}</div>
					<div class="detail-value text-purple-600 font-bold">
						{{ selectedDateData.working_hours }}h
					</div>
				</div>

				<!-- 排班信息 -->
				<div v-if="selectedDateData.shift" class="detail-item">
					<div class="detail-label">{{ __("Shift") }}</div>
					<div class="detail-value text-blue-600">
						{{ formatTime(selectedDateData.shift.start_time) }} - {{ formatTime(selectedDateData.shift.end_time) }}
					</div>
				</div>

				<!-- 空状态 -->
				<div
					v-if="!selectedDateData.attendance && !selectedDateData.shift"
					class="text-gray-400 text-sm text-center py-4"
				>
					{{ __("No records") }}
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { createResource } from "frappe-ui"
import { Dialog, Button } from "frappe-ui"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const __ = inject("$translate")
const firstOfMonth = ref(dayjs().date(1).startOf("D"))
const showDetailDialog = ref(false)
const selectedDate = ref(null)

const colorMap = {
	Present: "bg-green-300",
	"Work From Home": "bg-green-300",
	"Half Day": "bg-yellow-200",
	Absent: "bg-red-200",
	"On Leave": "bg-blue-300",
	Holiday: "bg-gray-300",
}

// __("Present"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Absent", "On Leave"]

const summary = computed(() => {
	const summary = {}

	for (const event of Object.values(calendarEvents.data || {})) {
		if (event && typeof event === "object" && event.attendance) {
			let updatedStatus = event.attendance === "Work From Home" ? "Present" : event.attendance
			if (updatedStatus in summary) {
				summary[updatedStatus] += 1
			} else {
				summary[updatedStatus] = 1
			}
		} else if (typeof event === "string") {
			// 兼容旧格式（向后兼容）
			let updatedStatus = event === "Work From Home" ? "Present" : event
			if (updatedStatus in summary) {
				summary[updatedStatus] += 1
			} else {
				summary[updatedStatus] = 1
			}
		}
	}

	return summary
})

const totalHours = computed(() => {
	let hours = 0
	for (const event of Object.values(calendarEvents.data || {})) {
		if (event && typeof event === "object" && event.working_hours) {
			hours += parseFloat(event.working_hours) || 0
		}
	}
	return hours.toFixed(1)
})

const getTitle = (key) => {
	const lang = frappe?.boot?.lang || "ja"
	const titles = {
		calendar: { ja: "考勤日历", zh: "考勤日历", en: "Attendance Calendar" },
		present: { ja: "今月の出勤", zh: "本月出勤", en: "Days Present" },
		hours: { ja: "勤務時間", zh: "工作时长", en: "Working Hours" },
		days: { ja: "日", zh: "天", en: "" }
	}
	return titles[key]?.[lang] || titles[key]?.ja || key
}

watch(
	() => firstOfMonth.value,
	() => {
		calendarEvents.fetch()
	}
)

const getEventOnDate = (date) => {
	const dateStr = firstOfMonth.value.date(date).format("YYYY-MM-DD")
	return calendarEvents.data?.[dateStr]
}

const hasShift = (date) => {
	const event = getEventOnDate(date)
	return event && typeof event === "object" && event.shift
}

const getDateClasses = (date) => {
	const event = getEventOnDate(date)
	if (!event) return ""

	// 如果是对象格式（新格式）
	if (typeof event === "object") {
		// 有考勤状态，使用考勤背景色
		if (event.attendance) {
			return colorMap[event.attendance] || ""
		}
		// 只有排班，使用浅蓝背景+蓝边框
		if (event.shift) {
			return "bg-blue-100 border-2 border-blue-500"
		}
	}

	// 兼容旧格式（字符串）
	if (typeof event === "string") {
		return colorMap[event] || ""
	}

	return ""
}

const showDateDetail = (date) => {
	selectedDate.value = firstOfMonth.value.date(date)
	showDetailDialog.value = true
}

const selectedDateData = computed(() => {
	if (!selectedDate.value) return null
	return getEventOnDate(selectedDate.value.date())
})

const formatDate = (date) => {
	return date.format("YYYY-MM-DD")
}

const formatTime = (timeStr) => {
	if (!timeStr) return ""
	// 时间格式可能是 "09:00:00" 或 "09:00"
	return timeStr.substring(0, 5)
}

const getStatusClass = (status) => {
	const classes = {
		"Present": "text-green-600",
		"Work From Home": "text-green-600",
		"Absent": "text-red-600",
		"On Leave": "text-blue-600",
		"Half Day": "text-orange-500",
		"Holiday": "text-gray-500"
	}
	return classes[status] || "text-gray-800"
}

// 日语简写星期（日、月、火、水、木、金、土）
const DAYS = ["日", "月", "火", "水", "木", "金", "土"]

//resources
const calendarEvents = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: true,
	cache: "hrms:attendance_calendar_events",
	makeParams() {
		return {
			employee: employee.data.name,
			from_date: firstOfMonth.value.format("YYYY-MM-DD"),
			to_date: firstOfMonth.value.endOf("M").format("YYYY-MM-DD"),
		}
	},
})
</script>

<style scoped>
.calendar-wrapper {
	display: flex;
	flex-direction: column;
	width: 100%;
	height: 100%;
	min-height: 0;
	gap: 8px;
}

.calendar-section {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-height: 0;
}

.section-title {
	font-size: 13px;
	font-weight: 600;
	color: #374151;
	margin-bottom: 4px;
	flex-shrink: 0;
}

.calendar-card {
	background: white;
	border-radius: 12px;
	padding: 12px 14px;
	box-shadow: 0 2px 8px rgba(0,0,0,0.05);
	flex: 1;
	display: flex;
	flex-direction: column;
	min-height: 0;
	overflow: hidden;
}

.month-nav {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 6px;
	flex-shrink: 0;
}

.month-label {
	font-size: 16px;
	font-weight: 700;
	color: #111827;
}

.calendar-grid {
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	gap: 6px 4px;
	flex: 1;
	align-content: start;
	min-height: 0;
}

.day-header {
	display: flex;
	justify-content: center;
	align-items: center;
	font-size: 12px;
	font-weight: 600;
	color: #9ca3af;
	padding: 4px 0;
}

.day-cell {
	display: flex;
	justify-content: center;
	align-items: center;
	aspect-ratio: 1;
}

.day-circle {
	width: 100%;
	max-width: 38px;
	aspect-ratio: 1;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
	position: relative;
	cursor: pointer;
	transition: all 0.15s;
	border: 2px solid #d1d5db;
	background: white;
}

.day-circle:hover {
	transform: scale(1.08);
	box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

/* 出勤状态颜色 */
.day-circle.bg-green-300 {
	background: #86efac;
	border-color: #22c55e;
}

.day-circle.bg-red-200 {
	background: #fecaca;
	border-color: #ef4444;
}

.day-circle.bg-blue-300 {
	background: #93c5fd;
	border-color: #3b82f6;
}

.day-circle.bg-yellow-200 {
	background: #fef08a;
	border-color: #eab308;
}

.day-circle.bg-gray-300 {
	background: #d1d5db;
	border-color: #9ca3af;
}

.day-number {
	font-size: 14px;
	font-weight: 600;
	color: #374151;
}

.shift-indicator {
	position: absolute;
	top: 0;
	right: 0;
	width: 6px;
	height: 6px;
	border-radius: 50%;
	background: #3b82f6;
	border: 1px solid white;
}

.shift-indicator.shift-only {
	width: 7px;
	height: 7px;
	background: #2563eb;
}

/* 统计区域 */
.stats-section {
	display: flex;
	flex-direction: column;
	gap: 6px;
	flex-shrink: 0;
}

.stats-row {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 6px;
}

.stat-card {
	background: white;
	border-radius: 10px;
	padding: 10px;
	display: flex;
	align-items: center;
	gap: 8px;
	box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.stat-icon {
	width: 36px;
	height: 36px;
	border-radius: 8px;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.stat-icon svg {
	width: 18px;
	height: 18px;
}

.present-icon {
	background: rgba(16, 185, 129, 0.1);
	color: #10b981;
}

.hours-icon {
	background: rgba(139, 92, 246, 0.1);
	color: #8b5cf6;
}

.stat-info {
	display: flex;
	flex-direction: column;
	gap: 1px;
}

.stat-value {
	font-size: 18px;
	font-weight: 700;
	color: #111827;
	line-height: 1;
}

.stat-unit {
	font-size: 12px;
	font-weight: 500;
	color: #6b7280;
	margin-left: 1px;
}

.stat-label {
	font-size: 10px;
	color: #6b7280;
}

/* 图例 */
.legend-row {
	display: flex;
	justify-content: space-around;
	background: white;
	border-radius: 8px;
	padding: 8px 4px;
	box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.legend-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 2px;
}

.legend-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
}

.legend-label {
	font-size: 10px;
	color: #6b7280;
	text-align: center;
}

.legend-count {
	font-size: 14px;
	font-weight: 700;
	color: #111827;
}

/* Dialog 样式 */
.detail-item {
	display: flex;
	justify-content: space-between;
	align-items: center;
	padding: 12px 0;
	border-bottom: 1px solid #f3f4f6;
}

.detail-item:last-child {
	border-bottom: none;
}

.detail-label {
	font-size: 14px;
	color: #6b7280;
}

.detail-value {
	font-size: 16px;
	font-weight: 600;
}
</style>
