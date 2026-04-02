<template>
	<BaseLayout :pageTitle="__('My Schedule')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 space-y-4">
				<!-- Month Navigation -->
				<div class="flex items-center justify-between">
					<button @click="prevMonth" class="p-2 rounded-lg hover:bg-gray-100">
						<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
						</svg>
					</button>
					<div class="text-lg font-semibold text-gray-800">
						{{ currentYear }}{{ __("年") }}{{ currentMonth }}{{ __("月") }}
					</div>
					<button @click="nextMonth" class="p-2 rounded-lg hover:bg-gray-100">
						<svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
					</button>
				</div>

				<!-- Weekday Headers -->
				<div class="grid grid-cols-7 gap-1 text-center text-xs font-medium">
					<div
						v-for="(day, idx) in weekdayHeaders"
						:key="day"
						:class="[idx === 0 ? 'text-red-500' : idx === 6 ? 'text-blue-500' : 'text-gray-500']"
					>
						{{ day }}
					</div>
				</div>

				<!-- Calendar Grid -->
				<div class="grid grid-cols-7 gap-1">
					<template v-for="(day, idx) in calendarDays" :key="idx">
						<div v-if="day.empty" class="aspect-square" />
						<div
							v-else
							:class="[
								'aspect-square rounded-lg flex flex-col items-center justify-center text-sm relative',
								day.hasShift ? 'bg-blue-50 border border-blue-200' : '',
								day.isHoliday ? 'bg-red-50' : '',
								day.isSunday && !day.hasShift ? 'bg-red-50/30' : '',
								day.isSaturday && !day.hasShift ? 'bg-blue-50/30' : '',
								!day.hasShift && !day.isHoliday && !day.isSunday && !day.isSaturday ? 'bg-white border border-gray-50' : '',
							]"
						>
							<span :class="[
								'text-sm',
								day.isHoliday || day.isSunday ? 'text-red-500' : '',
								day.isSaturday ? 'text-blue-500' : '',
								day.hasShift ? 'font-semibold text-blue-700' : '',
							]">
								{{ day.date }}
							</span>
							<span v-if="day.shift" class="text-[8px] leading-tight truncate max-w-full px-0.5 text-blue-600 font-medium">
								{{ day.shift }}
							</span>
						</div>
					</template>
				</div>

				<!-- Schedule List -->
				<div v-if="scheduleEntries.length" class="space-y-2">
					<div class="text-base font-semibold text-gray-800">{{ __("Schedule Details") }}</div>
					<div
						v-for="entry in scheduleEntries"
						:key="entry.name"
						class="flex items-center justify-between bg-white rounded-lg border border-gray-100 px-4 py-3"
					>
						<div>
							<div class="font-medium text-gray-800">{{ formatDate(entry.date) }}</div>
							<div class="text-sm text-gray-500">{{ entry.wr_shift_slot || __("Custom Time") }}</div>
						</div>
						<div class="text-right">
							<div class="text-sm font-medium text-gray-700">
								{{ entry.is_custom ? formatTimeRange(entry.custom_start_time, entry.custom_end_time) : "" }}
							</div>
							<div class="text-xs text-gray-400">{{ entry.hours }}h</div>
						</div>
					</div>
				</div>

				<div v-else-if="!scheduleResource.loading" class="text-center py-8">
					<div class="text-gray-400 text-sm">{{ __("No schedule for this month") }}</div>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ref, computed, inject, watch } from "vue"
import { createResource } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)

const weekdayHeaders = ["日", "月", "火", "水", "木", "金", "土"]

const scheduleResource = createResource({
	url: "work_roster.api.schedule.get_my_schedule",
	auto: false,
})

function loadSchedule() {
	scheduleResource.fetch({
		params: { month: currentMonth.value, year: currentYear.value },
	})
}

watch([currentYear, currentMonth], loadSchedule, { immediate: true })

const scheduleEntries = computed(() => scheduleResource.data || [])

const scheduleByDate = computed(() => {
	const map = {}
	for (const e of scheduleEntries.value) {
		const d = typeof e.date === "string" ? e.date : dayjs(e.date).format("YYYY-MM-DD")
		map[d] = e.wr_shift_slot || __("Custom")
	}
	return map
})

const calendarDays = computed(() => {
	const year = currentYear.value
	const month = currentMonth.value
	const firstDay = new Date(year, month - 1, 1)
	const lastDay = new Date(year, month, 0).getDate()
	let startWeekday = firstDay.getDay()

	const days = []
	for (let i = 0; i < startWeekday; i++) {
		days.push({ empty: true })
	}

	for (let d = 1; d <= lastDay; d++) {
		const dateObj = new Date(year, month - 1, d)
		const weekday = dateObj.getDay()
		const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`

		days.push({
			date: d,
			dateStr,
			weekday,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isHoliday: false,
			hasShift: !!scheduleByDate.value[dateStr],
			shift: scheduleByDate.value[dateStr] || "",
		})
	}

	return days
})

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

function formatDate(dateStr) {
	if (!dateStr) return ""
	return dayjs(dateStr).format("M/D (ddd)")
}

function formatTimeRange(start, end) {
	if (!start || !end) return ""
	return `${start.substring(0, 5)} - ${end.substring(0, 5)}`
}
</script>
