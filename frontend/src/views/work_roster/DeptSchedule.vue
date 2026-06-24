<template>
	<BaseLayout :pageTitle="t('pageTitle')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 pb-8 space-y-4">
				<div v-if="isLoading" class="text-center py-10">
					<div class="text-gray-400">{{ t("loading") }}</div>
				</div>

				<template v-else-if="period">
					<div class="text-center">
						<div class="text-lg font-semibold text-gray-800">{{ period.title || t("pageTitle") }}</div>
						<div class="text-sm text-gray-500 mt-1">{{ formatMonthTitle(period.year, period.month) }}</div>
					</div>

					<div class="flex flex-wrap items-center gap-3 rounded-xl bg-white border border-gray-100 px-4 py-3 text-xs text-gray-500">
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-red-100 border border-red-200"></span> {{ t("holiday") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-amber-300 border border-amber-400"></span> {{ t("saleEvent") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-blue-50 border border-blue-200"></span> {{ t("saturday") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-red-50 border border-red-200"></span> {{ t("sunday") }}</span>
						<span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-blue-500"></span> {{ t("scheduledCount") }}</span>
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
								@click="selectDay(day)"
								:class="[
									'min-h-[88px] rounded-xl border p-1.5 text-left align-top transition-all flex flex-col',
									day.isSelected ? 'ring-2 ring-blue-500 border-blue-300 shadow-sm' : 'border-gray-100',
									day.isHoliday ? 'bg-red-50' : '',
									day.isSunday && !day.isHoliday ? 'bg-red-50/40' : '',
									day.isSaturday ? 'bg-blue-50/50' : '',
									!day.isHoliday && !day.isSunday && !day.isSaturday ? 'bg-white' : '',
								]"
								:style="dayCellStyle(day)"
								:title="day.calendarEvent?.title || day.holidayName || ''"
							>
								<div class="flex items-start justify-between gap-1">
									<span :class="[
										'text-sm font-semibold',
										day.isHoliday || day.isSunday ? 'text-red-500' : '',
										day.isSaturday ? 'text-blue-500' : '',
										!day.isHoliday && !day.isSunday && !day.isSaturday ? 'text-gray-800' : '',
									]">
										{{ day.date }}
									</span>
									<div class="flex shrink-0 items-center gap-1">
										<span
											v-if="day.calendarEvent"
											class="h-2 w-2 rounded-full border border-white/80"
											:style="{ backgroundColor: day.calendarEvent.color || defaultSaleColor }"
										></span>
										<span
											v-if="day.entryCount"
											class="rounded-full bg-blue-500 px-1.5 py-0.5 text-[9px] font-semibold text-white"
										>
											{{ t("countSuffix", { count: day.entryCount }) }}
										</span>
									</div>
								</div>

								<div
									v-if="day.holidayName && !day.isWeeklyOff"
									class="mt-0.5 truncate text-[7px] leading-tight text-red-400"
								>
									{{ day.holidayName }}
								</div>
								<div
									v-if="day.calendarEvent"
									class="mt-0.5 truncate text-[7px] font-semibold leading-tight"
									:style="{ color: day.calendarEvent.color || defaultSaleColor }"
								>
									{{ day.calendarEvent.title }}
								</div>

								<div v-if="day.previewEntries.length" class="mt-1 space-y-1">
									<div
										v-for="entry in day.previewEntries"
										:key="entry.name"
										class="truncate rounded-md bg-white/80 px-1 py-0.5 text-[8px] leading-tight text-gray-700"
									>
										{{ entry.employee_name }}
									</div>
									<div
										v-if="day.entryCount > day.previewEntries.length"
										class="text-[8px] font-medium text-blue-600"
									>
										+{{ t("countSuffix", { count: day.entryCount - day.previewEntries.length }) }}
									</div>
								</div>
								<div v-else class="mt-auto text-[8px] text-gray-300">{{ t("emptyShort") }}</div>
							</button>
						</template>
					</div>

					<div class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
						<div class="px-4 py-3 border-b border-gray-100 bg-gray-50">
							<div class="text-base font-semibold text-gray-800">{{ selectedDayTitle }}</div>
							<div class="text-xs text-gray-500 mt-1">{{ t("selectedSummary", { count: selectedEntries.length }) }}</div>
							<div
								v-if="selectedDayEvent"
								class="mt-2 inline-flex items-center gap-1.5 rounded-full px-2 py-1 text-xs font-semibold"
								:style="saleEventPillStyle(selectedDayEvent)"
							>
								<span class="h-2 w-2 rounded-full bg-current"></span>
								{{ selectedDayEvent.title }}
							</div>
						</div>

						<div v-if="selectedEntries.length" class="divide-y divide-gray-50">
							<div
								v-for="entry in selectedEntries"
								:key="entry.name"
								class="flex items-center justify-between gap-3 px-4 py-3"
							>
								<div class="min-w-0">
									<div class="font-medium text-gray-800 truncate">{{ entry.employee_name }}</div>
									<div class="text-xs text-gray-500 mt-0.5">
										{{ entry.shift_label || entry.wr_shift_slot || t("customTime") }}
									</div>
								</div>
								<div class="text-right shrink-0">
									<div class="text-sm font-semibold text-gray-800">
										{{ entry.scheduled_time || getEntryTimeLabel(entry) }}
									</div>
									<div class="text-xs text-gray-400">{{ entry.hours || 0 }}h</div>
								</div>
							</div>
						</div>

						<div v-else class="text-center py-8">
							<div class="text-sm text-gray-400">{{ t("emptyDay") }}</div>
						</div>
					</div>
				</template>

				<div v-else class="text-center py-10">
					<div class="text-gray-400 text-sm">{{ t("periodMissing") }}</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, onMounted, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { useRoute } from "vue-router"
import { createResource } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const route = useRoute()

const periodId = computed(() => route.params.periodId)
const selectedDate = ref("")
const weekdayHeaderMap = {
	zh: ["日", "一", "二", "三", "四", "五", "六"],
	ja: ["日", "月", "火", "水", "木", "金", "土"],
	en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
}
const labels = {
	pageTitle: { zh: "部门排班", ja: "部門シフト", en: "Department Roster" },
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	holiday: { zh: "祝日", ja: "祝日", en: "Holiday" },
	saleEvent: { zh: "大促日", ja: "セール日", en: "Sale" },
	saturday: { zh: "周六", ja: "土曜", en: "Saturday" },
	sunday: { zh: "周日", ja: "日曜", en: "Sunday" },
	scheduledCount: { zh: "已排班人数", ja: "配置人数", en: "Scheduled" },
	countSuffix: { zh: "{count}人", ja: "{count}人", en: "{count}" },
	emptyShort: { zh: "暂无", ja: "なし", en: "Empty" },
	emptyDay: { zh: "当天暂无排班", ja: "当日のシフトはありません", en: "No roster for this day" },
	periodMissing: { zh: "未找到排班周期", ja: "シフト期間が見つかりません", en: "Roster period not found" },
	defaultDayTitle: { zh: "当日排班", ja: "当日のシフト", en: "Daily Roster" },
	selectedSummary: { zh: "已排班 {count} 人", ja: "{count} 人を配置済み", en: "{count} people scheduled" },
	customTime: { zh: "自定义", ja: "カスタム", en: "Custom" },
}
const defaultSaleColor = "#F59E0B"

const weekdayHeaders = computed(() => weekdayHeaderMap[getLang()] || weekdayHeaderMap.zh)

const scheduleResource = createResource({
	url: "work_roster.api.schedule.get_department_schedule",
	auto: false,
})

const periodResource = createResource({
	url: "frappe.client.get",
	auto: false,
})

const holidaysResource = createResource({
	url: "work_roster.api.schedule.get_holidays",
	auto: false,
})

const calendarEventsResource = createResource({
	url: "work_roster.api.schedule.get_calendar_events",
	auto: false,
})

const period = computed(() => periodResource.data || null)
const scheduleEntries = computed(() => scheduleResource.data || [])
const isLoading = computed(() => scheduleResource.loading || periodResource.loading || holidaysResource.loading || calendarEventsResource.loading)

const holidayMap = computed(() => {
	const map = {}
	for (const holiday of holidaysResource.data || []) {
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

const calendarEventMap = computed(() => {
	const map = {}
	for (const event of calendarEventsResource.data || []) {
		const dateStr = typeof event.event_date === "string"
			? event.event_date
			: dayjs(event.event_date).format("YYYY-MM-DD")
		if (!map[dateStr] || event.event_type === "Major Sale") {
			map[dateStr] = event
		}
	}
	return map
})

const dayScheduleMap = computed(() => {
	const map = {}
	for (const entry of scheduleEntries.value) {
		const dateStr = typeof entry.date === "string" ? entry.date : dayjs(entry.date).format("YYYY-MM-DD")
		if (!map[dateStr]) {
			map[dateStr] = []
		}
		map[dateStr].push(entry)
	}
	for (const dateStr of Object.keys(map)) {
		map[dateStr].sort((a, b) => a.employee_name.localeCompare(b.employee_name))
	}
	return map
})

const calendarDays = computed(() => {
	if (!period.value) return []

	const year = period.value.year
	const month = period.value.month
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
		const holiday = holidayMap.value[dateStr]
		const calendarEvent = calendarEventMap.value[dateStr] || null
		const entries = dayScheduleMap.value[dateStr] || []

		days.push({
			date: d,
			dateStr,
			weekday,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isHoliday: !!holiday && !holiday.weekly_off,
			isWeeklyOff: !!holiday?.weekly_off,
			holidayName: holiday?.description || "",
			calendarEvent,
			entryCount: entries.length,
			previewEntries: entries.slice(0, 2),
			isSelected: selectedDate.value === dateStr,
		})
	}

	return days
})

const selectedEntries = computed(() => {
	return dayScheduleMap.value[selectedDate.value] || []
})

const selectedDayEvent = computed(() => {
	return calendarEventMap.value[selectedDate.value] || null
})

const selectedDayTitle = computed(() => {
	if (!selectedDate.value) return t("defaultDayTitle")
	return formatDate(selectedDate.value)
})

function loadData() {
	if (!periodId.value) return
	scheduleResource.fetch({ wr_period: periodId.value })
	periodResource.fetch({
		doctype: "WR Period",
		name: periodId.value,
	})
}

function selectDay(day) {
	if (!day?.dateStr) return
	selectedDate.value = day.dateStr
}

function getEntryTimeLabel(entry) {
	if (entry.is_custom) {
		return formatTimeRange(entry.custom_start_time, entry.custom_end_time)
	}
	return entry.wr_shift_slot || formatTimeRange(entry.custom_start_time, entry.custom_end_time)
}

function getLang() {
	return frappe?.boot?.lang || "zh"
}

function t(key, params = null) {
	const text = labels[key]?.[getLang()] || labels[key]?.zh || __(key)
	if (!params) return text
	return text.replace(/\{(\w+)\}/g, (_, name) => `${params[name] ?? ""}`)
}

function formatMonthTitle(year, month) {
	if (getLang() === "en") {
		return dayjs(`${year}-${String(month).padStart(2, "0")}-01`).format("MMMM YYYY")
	}
	return `${year}年${month}月`
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const weekdayMap = weekdayHeaderMap[getLang()] || weekdayHeaderMap.zh
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
	return `${start.substring(0, 5)}-${end.substring(0, 5)}`
}

function dayCellStyle(day) {
	if (!day.calendarEvent) return {}
	const color = day.calendarEvent.color || defaultSaleColor
	return {
		backgroundColor: tintColor(color, day.isSelected ? 0.72 : 0.84),
		borderColor: color,
	}
}

function saleEventPillStyle(event) {
	const color = event.color || defaultSaleColor
	return {
		backgroundColor: tintColor(color, 0.78),
		color: readableTextColor(tintColor(color, 0.78)),
	}
}

function readableTextColor(color) {
	const rgb = hexToRgb(color)
	if (!rgb) return "#111827"
	const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
	return brightness < 150 ? "#ffffff" : "#111827"
}

function tintColor(color, whiteMix) {
	const rgb = hexToRgb(color)
	if (!rgb) return color
	const mix = Math.max(0, Math.min(1, whiteMix))
	const r = Math.round(rgb.r + (255 - rgb.r) * mix)
	const g = Math.round(rgb.g + (255 - rgb.g) * mix)
	const b = Math.round(rgb.b + (255 - rgb.b) * mix)
	return `rgb(${r}, ${g}, ${b})`
}

function hexToRgb(color) {
	const match = String(color || "").trim().match(/^#?([0-9a-f]{6})$/i)
	if (!match) return null
	const intValue = parseInt(match[1], 16)
	return {
		r: (intValue >> 16) & 255,
		g: (intValue >> 8) & 255,
		b: intValue & 255,
	}
}

watch(period, (value) => {
	if (!value) return
	holidaysResource.fetch({
		holiday_list: value.holiday_list,
		month: value.month,
		year: value.year,
	})
	calendarEventsResource.fetch({
		month: value.month,
		year: value.year,
		department_category: value.department_category,
	})
})

watch(calendarDays, (days) => {
	const validDays = days.filter((day) => !day.empty)
	if (!validDays.length) {
		selectedDate.value = ""
		return
	}
	if (selectedDate.value && validDays.some((day) => day.dateStr === selectedDate.value)) {
		return
	}
	const firstScheduledDay = validDays.find((day) => day.entryCount)
	selectedDate.value = (firstScheduledDay || validDays[0]).dateStr
}, { immediate: true })

onMounted(() => {
	loadData()
})

onIonViewWillEnter(() => {
	loadData()
})
</script>
