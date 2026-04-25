<template>
	<BaseLayout :pageTitle="t('pageTitle')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 pb-8 space-y-4">
				<div v-if="isLoading" class="text-center py-10">
					<div class="text-gray-400">{{ t("loading") }}</div>
				</div>

				<template v-else>
					<div class="flex items-center justify-between">
						<button @click="prevMonth" class="p-2 rounded-lg hover:bg-gray-100">
							<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
							</svg>
						</button>
						<div class="text-lg font-semibold text-gray-800">
							{{ formatMonthTitle(currentYear, currentMonth) }}
						</div>
						<button @click="nextMonth" class="p-2 rounded-lg hover:bg-gray-100">
							<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</button>
					</div>

					<div class="flex flex-wrap items-center gap-3 rounded-xl bg-white border border-gray-100 px-4 py-3 text-xs text-gray-500">
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-red-100 border border-red-200"></span> {{ t("holiday") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-blue-50 border border-blue-200"></span> {{ t("saturday") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-red-50 border border-red-200"></span> {{ t("sunday") }}</span>
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

					<div class="grid grid-cols-7 gap-1.5">
						<template v-for="(day, idx) in calendarDays" :key="idx">
							<div v-if="day.empty" class="aspect-square" />
							<button
								v-else
								@click="openDayDetail(day)"
								:class="[
									'min-h-[82px] rounded-xl border px-1.5 py-1.5 text-left transition-all flex flex-col shadow-sm',
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

					<div v-if="scheduleEntries.length" class="space-y-2">
						<div class="text-base font-semibold text-gray-800">{{ t("scheduleDetails") }}</div>
						<div
							v-for="entry in scheduleEntries"
							:key="entry.name"
							class="flex items-center justify-between bg-white rounded-lg border border-gray-100 px-4 py-3"
						>
							<div>
								<div class="font-medium text-gray-800">{{ formatDate(entry.date) }}</div>
								<div class="text-sm text-gray-500">{{ entry.shift_label || t("customTime") }}</div>
							</div>
							<div class="text-right">
								<div class="text-sm font-medium text-gray-700">
									{{ entry.scheduled_time || formatTimeRange(entry.custom_start_time, entry.custom_end_time) }}
								</div>
								<div class="text-xs text-gray-400">{{ entry.hours }}h</div>
							</div>
						</div>
					</div>

					<div v-else class="text-center py-8">
						<div class="text-gray-400 text-sm">{{ t("emptyMonth") }}</div>
					</div>
				</template>
			</div>

			<Dialog v-model="showDetailDialog">
				<template #body-title>
					<h2 class="text-lg font-bold text-gray-800">
						{{ selectedDate ? formatDate(selectedDate) : "" }}
					</h2>
				</template>
				<template #body-content>
					<div class="space-y-3" v-if="selectedDayData">
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

						<div
							v-if="selectedDayData.in_time || selectedDayData.out_time"
							class="grid grid-cols-2 gap-3"
						>
							<div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
								<div class="text-xs font-medium text-gray-500">{{ t("checkIn") }}</div>
								<div class="mt-1 text-base font-semibold text-green-600">{{ selectedDayData.in_time || "--:--" }}</div>
							</div>
							<div class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm">
								<div class="text-xs font-medium text-gray-500">{{ t("checkOut") }}</div>
								<div class="mt-1 text-base font-semibold text-red-600">{{ selectedDayData.out_time || "--:--" }}</div>
							</div>
						</div>

						<div
							v-if="selectedDayData.working_hours"
							class="rounded-xl border border-gray-100 bg-white px-4 py-3 shadow-sm"
						>
							<div class="text-xs font-medium text-gray-500">{{ t("workingHours") }}</div>
							<div class="mt-1 text-base font-semibold text-purple-600">{{ selectedDayData.working_hours }}h</div>
						</div>

						<div
							v-if="selectedDayData.roster"
							class="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 shadow-sm"
						>
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
							class="text-gray-400 text-sm text-center py-4"
						>
							{{ t("noRecords") }}
						</div>
					</div>
				</template>
			</Dialog>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ref, computed, inject, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource, Dialog } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const __ = inject("$translate")

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)
const showDetailDialog = ref(false)
const selectedDate = ref("")

const labels = {
	pageTitle: { zh: "我的排班", ja: "私のシフト", en: "My Roster" },
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	holiday: { zh: "祝日", ja: "祝日", en: "Holiday" },
	saturday: { zh: "周六", ja: "土曜", en: "Saturday" },
	sunday: { zh: "周日", ja: "日曜", en: "Sunday" },
	rosterOnly: { zh: "仅排班", ja: "シフトのみ", en: "Roster Only" },
	scheduleDetails: { zh: "排班明细", ja: "シフト詳細", en: "Roster Details" },
	emptyMonth: { zh: "当前月份暂无排班", ja: "この月のシフトはありません", en: "No roster for this month" },
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
		const attendance = attendanceMap.value[dateStr]
		const roster = rosterMap.value[dateStr]
		const holiday = holidayMap.value[dateStr]
		const hasAttendance = !!attendance?.attendance
		const hasRoster = !!roster
		const attendanceLabel = hasAttendance ? getAttendanceShortLabel(attendance.attendance) : ""

		days.push({
			date: d,
			dateStr,
			weekday,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isHoliday: !!holiday && !holiday.weekly_off,
			isWeeklyOff: !!holiday?.weekly_off,
			holidayName: holiday?.description || "",
			attendance: attendance?.attendance || "",
			hasAttendance,
			hasRoster,
			primaryText: hasAttendance
				? attendanceLabel
				: (roster?.shift_label || ""),
			secondaryText: hasAttendance
				? (roster?.shift_label || "")
				: (roster?.scheduled_time || ""),
		})
	}

	return days
})

const selectedDayData = computed(() => {
	if (!selectedDate.value) return null
	const attendance = attendanceMap.value[selectedDate.value] || {}
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

watch([currentYear, currentMonth], loadData, { immediate: true })

watch(calendarDays, (days) => {
	const validDays = days.filter((day) => !day.empty)
	if (!validDays.length) {
		selectedDate.value = ""
		return
	}
	if (selectedDate.value && validDays.some((day) => day.dateStr === selectedDate.value)) {
		return
	}
	const todayStr = dayjs().format("YYYY-MM-DD")
	const preferredDay = validDays.find((day) => day.dateStr === todayStr)
		|| validDays.find((day) => day.hasAttendance || day.hasRoster)
		|| validDays[0]
	selectedDate.value = preferredDay?.dateStr || ""
})

onIonViewWillEnter(() => {
	loadData()
})
</script>
