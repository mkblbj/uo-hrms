<template>
	<div class="flex flex-col w-full gap-5" v-if="calendarEvents.data">
		<div class="text-lg text-gray-800 font-bold">{{ __("Attendance Calendar") }}</div>

		<div class="flex flex-col gap-6 bg-white py-6 px-3.5 rounded-lg border-none">
			<!-- Month Change -->
			<div class="flex flex-row justify-between items-center px-4">
				<Button
					icon="chevron-left"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.subtract(1, 'M')"
				/>
				<span class="text-lg text-gray-800 font-bold">
					{{ firstOfMonth.format("MMMM") }} {{ firstOfMonth.format("YYYY") }}
				</span>
				<Button
					icon="chevron-right"
					variant="ghost"
					@click="firstOfMonth = firstOfMonth.add(1, 'M')"
				/>
			</div>

			<!-- Calendar -->
			<div class="grid grid-cols-7 gap-y-3">
				<div
					v-for="day in DAYS"
					class="flex justify-center text-gray-600 text-sm font-medium leading-6"
				>
					{{ day }}
				</div>
				<div v-for="_ in firstOfMonth.get('d')" />
				<div v-for="index in firstOfMonth.endOf('M').get('D')">
					<div
						class="h-10 w-10 flex rounded-full mx-auto relative cursor-pointer transition-all hover:scale-110"
						:class="getDateClasses(index)"
						@click="showDateDetail(index)"
					>
						<!-- 排班指示器 -->
						<span
							v-if="hasShift(index)"
							class="absolute top-0 right-0 h-2.5 w-2.5 rounded-full bg-blue-500 border border-white"
							:class="getEventOnDate(index)?.attendance ? '' : 'h-3 w-3 bg-blue-600'"
						/>
						<span class="text-gray-800 text-sm font-medium m-auto">
							{{ index }}
						</span>
					</div>
				</div>
			</div>

			<hr />

			<!-- Summary -->
			<div class="grid grid-cols-4 mx-2">
				<div v-for="status in summaryStatuses" class="flex flex-col gap-1">
					<div class="flex flex-row gap-1 items-center">
						<span class="rounded full h-3 w-3" :class="colorMap[status]" />
						<span class="text-gray-600 text-sm font-medium leading-5"> {{ __(status) }} </span>
					</div>
					<span class="text-gray-800 text-base font-semibold leading-6 mx-auto">
						{{ summary[status] || 0 }}
					</span>
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
			<div class="space-y-4" v-if="selectedDateData">
				<!-- 考勤状态 -->
				<div v-if="selectedDateData.attendance" class="mb-4">
					<div class="text-sm text-gray-600 mb-1">{{ __("Attendance Status") }}</div>
					<div class="font-medium text-gray-800">{{ __(selectedDateData.attendance) }}</div>
				</div>

				<!-- 排班信息 -->
				<div v-if="selectedDateData.shift" class="mb-4">
					<div class="text-sm text-gray-600 mb-1">{{ __("Shift Information") }}</div>
					<div
						v-if="selectedDateData.shift.start_time && selectedDateData.shift.end_time"
						class="font-medium text-gray-800"
					>
						{{ formatTime(selectedDateData.shift.start_time) }} - {{ formatTime(selectedDateData.shift.end_time) }}
					</div>
					<div
						v-else
						class="font-medium text-gray-800"
					>
						{{ __("Scheduled") }}
					</div>
				</div>

				<!-- 空状态 -->
				<div
					v-if="!selectedDateData.attendance && !selectedDateData.shift"
					class="text-gray-500 text-sm"
				>
					{{ __("No attendance or shift information for this date") }}
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

// __("Present"), __("Half Day"), __("Absent"), __("On Leave"), __("Work From Home")
const summaryStatuses = ["Present", "Half Day", "Absent", "On Leave"]

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

const getFirstLetter = (s) => Array.from(s.trim())[0] // Unicode

const DAYS = [
	getFirstLetter(__("Sunday")),
	getFirstLetter(__("Monday")),
	getFirstLetter(__("Tuesday")),
	getFirstLetter(__("Wednesday")),
	getFirstLetter(__("Thursday")),
	getFirstLetter(__("Friday")),
	getFirstLetter(__("Saturday")),
]

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
