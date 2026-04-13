<template>
	<div class="flex h-full min-h-0 w-full flex-col gap-4">
		<div v-if="isLoading" class="flex-1 py-10 text-center">
			<div class="text-gray-400">{{ t("loading") }}</div>
		</div>

		<template v-else>
			<div class="flex items-center justify-between">
				<button @click="prevMonth" class="rounded-lg p-2 hover:bg-gray-100">
					<svg class="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
				</button>
				<div class="text-lg font-semibold text-gray-800">
					{{ formatMonthTitle(currentYear, currentMonth) }}
				</div>
				<button @click="nextMonth" class="rounded-lg p-2 hover:bg-gray-100">
					<svg class="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>
			</div>

			<div class="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-white px-4 py-3 text-xs text-gray-500">
				<span class="flex items-center gap-1"><span class="h-3 w-3 rounded border border-red-200 bg-red-100"></span> {{ t("holiday") }}</span>
				<span class="flex items-center gap-1">
					<span class="flex h-3 w-3.5 overflow-hidden rounded border border-gray-200">
						<span class="h-full w-1/2 border-r border-blue-100 bg-blue-50"></span>
						<span class="h-full w-1/2 bg-red-50"></span>
					</span>
					{{ t("weekend") }}
				</span>
				<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-blue-600"></span> {{ t("rosterOnly") }}</span>
			</div>

			<div class="grid grid-cols-7 gap-1 text-center text-xs font-medium">
				<div
					v-for="(day, idx) in weekdayHeaders"
					:key="day"
					:class="[idx === 0 ? 'text-red-500' : idx === 6 ? 'text-blue-500' : 'text-gray-500']"
				>
					{{ day }}
				</div>
			</div>

			<div class="flex-1 min-h-0">
				<div class="grid h-full grid-cols-7 gap-1.5" :style="calendarGridStyle">
					<template v-for="(day, idx) in calendarDays" :key="idx">
						<div v-if="day.empty" class="h-full rounded-xl" />
						<button
							v-else
							@click="openDayDetail(day)"
							:class="[
								'h-full min-h-0 min-w-0 overflow-hidden rounded-xl border px-1.5 py-1.5 text-left shadow-sm transition-all flex flex-col',
								getDayCardClass(day),
							]"
						>
							<div class="flex items-start justify-between gap-1">
								<span :class="['text-sm font-semibold', getDayNumberClass(day)]">
									{{ day.date }}
								</span>
								<span
									v-if="day.attendance"
									class="shrink-0 rounded-full px-1.5 py-0.5 text-[8px] font-semibold"
									:class="getAttendanceBadgeClass(day.attendance)"
								>
									{{ getAttendanceShortLabel(day.attendance) }}
								</span>
							</div>

							<div
								v-if="day.holidayName && !day.attendance"
								class="mt-0.5 truncate text-[7px] leading-tight text-red-400"
							>
								{{ day.holidayName }}
							</div>

							<div
								v-if="day.primaryText"
								class="mt-1 truncate text-[10px] font-semibold leading-tight"
								:class="day.hasAttendance ? 'text-gray-800' : day.hasRoster ? 'text-white' : 'text-gray-600'"
							>
								{{ day.primaryText }}
							</div>

							<div
								v-if="day.secondaryText"
								class="mt-0.5 truncate text-[8px] leading-tight"
								:class="day.hasRoster && !day.hasAttendance ? 'text-blue-100' : 'text-gray-500'"
							>
								{{ day.secondaryText }}
							</div>
						</button>
					</template>
				</div>
			</div>
		</template>

		<Dialog v-model="showDetailDialog">
			<template #body-title>
				<h2 class="text-lg font-bold text-gray-800">
					{{ selectedDate ? formatDate(selectedDate) : "" }}
				</h2>
			</template>
			<template #body-content>
				<div v-if="selectedDayData" class="space-y-3">
					<div v-if="selectedDayData.holidayName" class="rounded-xl border border-red-100 bg-red-50 px-4 py-3">
						<div class="text-xs font-medium text-red-500">{{ t("holiday") }}</div>
						<div class="mt-1 text-sm font-semibold text-red-700">{{ selectedDayData.holidayName }}</div>
					</div>

					<div v-if="selectedDayData.attendance" class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
						<div class="text-xs font-medium text-gray-500">{{ t("attendanceStatus") }}</div>
						<div class="mt-1 text-base font-semibold" :class="getStatusClass(selectedDayData.attendance)">
							{{ getAttendanceLabel(selectedDayData.attendance) }}
						</div>
					</div>

					<div v-if="selectedDayData.in_time || selectedDayData.out_time" class="grid grid-cols-2 gap-3">
						<div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
							<div class="text-xs font-medium text-gray-500">{{ t("checkIn") }}</div>
							<div class="mt-1 text-base font-semibold text-green-600">{{ selectedDayData.in_time || "--:--" }}</div>
						</div>
						<div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
							<div class="text-xs font-medium text-gray-500">{{ t("checkOut") }}</div>
							<div class="mt-1 text-base font-semibold text-red-600">{{ selectedDayData.out_time || "--:--" }}</div>
						</div>
					</div>

					<div v-if="selectedDayData.working_hours" class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
						<div class="text-xs font-medium text-gray-500">{{ t("workingHours") }}</div>
						<div class="mt-1 text-base font-semibold text-purple-600">{{ selectedDayData.working_hours }}h</div>
					</div>

					<div v-if="selectedDayData.roster" class="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 shadow-sm">
						<div class="text-xs font-medium text-blue-500">{{ t("rosterShift") }}</div>
						<div class="mt-1 text-base font-semibold text-blue-700">
							{{ selectedDayData.roster.shift_label || t("customTime") }}
						</div>
						<div class="mt-1 text-sm text-blue-600">
							{{ selectedDayData.roster.scheduled_time || formatTimeRange(selectedDayData.roster.custom_start_time, selectedDayData.roster.custom_end_time) }}
						</div>
					</div>

					<div
						v-if="!selectedDayData.attendance && !selectedDayData.roster && !selectedDayData.holidayName"
						class="py-4 text-center text-sm text-gray-400"
					>
						{{ t("noRecords") }}
					</div>
				</div>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource, Dialog } from "frappe-ui"

import {
	getCalendarGridStyle,
	getCalendarWeekCount,
	padCalendarDaysToFullWeeks,
} from "@/components/attendanceCalendarLayout"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const __ = inject("$translate")

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)
const showDetailDialog = ref(false)
const selectedDate = ref("")

const labels = {
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	holiday: { zh: "祝日", ja: "祝日", en: "Holiday" },
	weekend: { zh: "周末", ja: "週末", en: "Weekend" },
	rosterOnly: { zh: "仅排班", ja: "シフトのみ", en: "Roster Only" },
	customTime: { zh: "自定义时段", ja: "カスタム時間", en: "Custom Time" },
	attendanceStatus: { zh: "考勤状态", ja: "勤怠ステータス", en: "Attendance Status" },
	checkIn: { zh: "签到", ja: "出勤", en: "Check In" },
	checkOut: { zh: "签退", ja: "退勤", en: "Check Out" },
	workingHours: { zh: "工作时长", ja: "勤務時間", en: "Working Hours" },
	rosterShift: { zh: "排班班次", ja: "シフト枠", en: "Roster Shift" },
	noRecords: { zh: "当天暂无记录", ja: "当日の記録はありません", en: "No records for this day" },
	attendancePresent: { zh: "出勤", ja: "出勤", en: "Present" },
	attendanceWFH: { zh: "居家", ja: "在宅", en: "WFH" },
	attendanceHalfDay: { zh: "半天", ja: "半日", en: "Half Day" },
	attendanceAbsent: { zh: "休息", ja: "休み", en: "Rest" },
	attendanceHoliday: { zh: "休息", ja: "休日", en: "Holiday" },
	attendanceOnLeave: { zh: "请假", ja: "休暇", en: "On Leave" },
}

const weekdayLabels = {
	zh: ["日", "一", "二", "三", "四", "五", "六"],
	ja: ["日", "月", "火", "水", "木", "金", "土"],
	en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
}

const attendanceStatusMap = {
	Present: "attendancePresent",
	"Work From Home": "attendanceWFH",
	"Half Day": "attendanceHalfDay",
	Absent: "attendanceAbsent",
	Holiday: "attendanceHoliday",
	"On Leave": "attendanceOnLeave",
}

const weekdayHeaders = computed(() => weekdayLabels[getLang()] || weekdayLabels.zh)

const rosterCalendarResource = createResource({
	url: "work_roster.api.schedule.get_my_schedule_calendar_data",
	auto: false,
})

const attendanceResource = createResource({
	url: "hrms.api.get_attendance_calendar_events",
	auto: false,
	cache: false,
})

const isLoading = computed(() => rosterCalendarResource.loading || attendanceResource.loading)
const scheduleEntries = computed(() => rosterCalendarResource.data?.entries || [])

const rosterMap = computed(() => {
	const map = {}
	for (const entry of scheduleEntries.value) {
		const dateStr = typeof entry.date === "string" ? entry.date : dayjs(entry.date).format("YYYY-MM-DD")
		map[dateStr] = entry
	}
	return map
})

const holidayMap = computed(() => {
	const map = {}
	for (const holiday of rosterCalendarResource.data?.holidays || []) {
		const dateStr = typeof holiday.holiday_date === "string"
			? holiday.holiday_date
			: dayjs(holiday.holiday_date).format("YYYY-MM-DD")
		map[dateStr] = {
			description: holiday.description,
			weekly_off: holiday.weekly_off,
		}
	}
	return map
})

const attendanceMap = computed(() => attendanceResource.data || {})

const calendarDays = computed(() => {
	const year = currentYear.value
	const month = currentMonth.value
	const firstDay = new Date(year, month - 1, 1)
	const lastDay = new Date(year, month, 0).getDate()
	const startWeekday = firstDay.getDay()
	const days = []

	for (let i = 0; i < startWeekday; i++) {
		days.push({ empty: true })
	}

	for (let d = 1; d <= lastDay; d++) {
		const dateObj = new Date(year, month - 1, d)
		const weekday = dateObj.getDay()
		const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`
		const rawAttendance = attendanceMap.value[dateStr] || null
		const attendanceEntry = typeof rawAttendance === "string" ? { attendance: rawAttendance } : (rawAttendance || {})
		const roster = rosterMap.value[dateStr] || null
		const holiday = holidayMap.value[dateStr]
		const hasAttendance = !!attendanceEntry.attendance
		const hasRoster = !!roster
		const attendanceLabel = hasAttendance ? getAttendanceShortLabel(attendanceEntry.attendance) : ""

		days.push({
			date: d,
			dateStr,
			weekday,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isHoliday: !!holiday && !holiday.weekly_off,
			isWeeklyOff: !!holiday?.weekly_off,
			holidayName: holiday?.description || "",
			attendance: attendanceEntry.attendance || "",
			hasAttendance,
			hasRoster,
			primaryText: hasAttendance ? attendanceLabel : (roster?.shift_label || ""),
			secondaryText: hasAttendance ? (roster?.shift_label || "") : (roster?.scheduled_time || ""),
		})
	}

	return padCalendarDaysToFullWeeks(days)
})

const weekCount = computed(() => getCalendarWeekCount(calendarDays.value))
const calendarGridStyle = computed(() => getCalendarGridStyle(weekCount.value))

const selectedDayData = computed(() => {
	if (!selectedDate.value) return null
	const rawAttendance = attendanceMap.value[selectedDate.value] || null
	const attendance = typeof rawAttendance === "string" ? { attendance: rawAttendance } : (rawAttendance || {})
	const roster = rosterMap.value[selectedDate.value] || null
	const holiday = holidayMap.value[selectedDate.value] || null
	return {
		...attendance,
		roster,
		holidayName: holiday?.description || "",
		isHoliday: !!holiday && !holiday.weekly_off,
	}
})

function getLang() {
	return frappe?.boot?.lang || "zh"
}

function t(key) {
	return labels[key]?.[getLang()] || labels[key]?.zh || __(key)
}

function loadData() {
	const fromDate = `${currentYear.value}-${String(currentMonth.value).padStart(2, "0")}-01`
	const toDate = dayjs(fromDate).endOf("month").format("YYYY-MM-DD")
	rosterCalendarResource.fetch({ month: currentMonth.value, year: currentYear.value })
	if (employee?.data?.name) {
		attendanceResource.fetch({
			employee: employee.data.name,
			from_date: fromDate,
			to_date: toDate,
		})
	}
}

function openDayDetail(day) {
	if (!day?.dateStr) return
	selectedDate.value = day.dateStr
	showDetailDialog.value = true
}

function prevMonth() {
	if (currentMonth.value === 1) {
		currentMonth.value = 12
		currentYear.value--
	} else {
		currentMonth.value--
	}
}

function nextMonth() {
	if (currentMonth.value === 12) {
		currentMonth.value = 1
		currentYear.value++
	} else {
		currentMonth.value++
	}
}

function getAttendanceLabel(status) {
	return t(attendanceStatusMap[status] || status)
}

function getAttendanceShortLabel(status) {
	const map = {
		Present: { zh: "出勤", ja: "出勤", en: "IN" },
		"Work From Home": { zh: "居家", ja: "在宅", en: "WFH" },
		"Half Day": { zh: "半天", ja: "半日", en: "1/2" },
		Absent: { zh: "休", ja: "休", en: "REST" },
		Holiday: { zh: "休", ja: "休", en: "OFF" },
		"On Leave": { zh: "假", ja: "休", en: "LV" },
	}
	return map[status]?.[getLang()] || status
}

function getDayCardClass(day) {
	const classes = []
	if (day.hasAttendance) {
		classes.push(getAttendanceCardClass(day.attendance))
	} else if (day.hasRoster) {
		classes.push("bg-blue-600 border-blue-600 text-white")
	} else if (day.isHoliday) {
		classes.push("bg-red-50 border-red-200")
	} else if (day.isSunday) {
		classes.push("bg-red-50/50 border-red-100")
	} else if (day.isSaturday) {
		classes.push("bg-blue-50/60 border-blue-100")
	} else {
		classes.push("bg-white border-gray-100")
	}

	if ((day.isHoliday || day.isSunday) && (day.hasAttendance || day.hasRoster)) {
		classes.push("ring-1 ring-red-200")
	} else if (day.isSaturday && (day.hasAttendance || day.hasRoster)) {
		classes.push("ring-1 ring-blue-200")
	}

	return classes.join(" ")
}

function getAttendanceCardClass(status) {
	const classes = {
		Present: "bg-green-100 border-green-300",
		"Work From Home": "bg-green-100 border-green-300",
		"Half Day": "bg-yellow-100 border-yellow-300",
		Absent: "bg-slate-100 border-slate-300",
		Holiday: "bg-gray-100 border-gray-300",
		"On Leave": "bg-blue-100 border-blue-300",
	}
	return classes[status] || "bg-white border-gray-100"
}

function getDayNumberClass(day) {
	if (day.hasRoster && !day.hasAttendance) return "text-white"
	if (day.isHoliday || day.isSunday) return "text-red-500"
	if (day.isSaturday) return "text-blue-500"
	return "text-gray-800"
}

function getAttendanceBadgeClass(status) {
	const classes = {
		Present: "bg-green-200 text-green-700",
		"Work From Home": "bg-green-200 text-green-700",
		"Half Day": "bg-yellow-200 text-yellow-700",
		Absent: "bg-slate-200 text-slate-700",
		Holiday: "bg-gray-200 text-gray-600",
		"On Leave": "bg-blue-200 text-blue-700",
	}
	return classes[status] || "bg-gray-100 text-gray-600"
}

function getStatusClass(status) {
	const classes = {
		Present: "text-green-600",
		"Work From Home": "text-green-600",
		Absent: "text-slate-600",
		"On Leave": "text-blue-600",
		"Half Day": "text-orange-500",
		Holiday: "text-gray-500",
	}
	return classes[status] || "text-gray-800"
}

function formatMonthTitle(year, month) {
	if (getLang() === "en") {
		return dayjs(`${year}-${String(month).padStart(2, "0")}-01`).format("MMMM YYYY")
	}
	return `${year}年${month}月`
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const weekdayMap = weekdayLabels[getLang()] || weekdayLabels.zh
	const date = dayjs(dateStr)
	if (getLang() === "en") {
		return `${date.format("M/D")} (${weekdayMap[date.day()]})`
	}
	if (getLang() === "ja") {
		return `${date.format("M/D")}（${weekdayMap[date.day()]}）`
	}
	return `${date.format("M/D")}（周${weekdayMap[date.day()]}）`
}

function formatTimeRange(start, end) {
	if (!start || !end) return t("customTime")
	return `${start.substring(0, 5)} - ${end.substring(0, 5)}`
}

watch([currentYear, currentMonth, () => employee?.data?.name], loadData, { immediate: true })

onIonViewWillEnter(() => {
	loadData()
})
</script>
