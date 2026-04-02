<template>
	<BaseLayout :pageTitle="__('Submit Preference')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 space-y-4">
				<div v-if="periodResource.loading" class="text-center py-10">
					<div class="text-gray-400">{{ __("Loading...") }}</div>
				</div>

				<template v-else-if="period">
					<div class="text-center">
						<div class="text-lg font-semibold text-gray-800">{{ period.title }}</div>
						<div class="text-sm text-gray-500 mt-1">
							{{ __("Deadline") }}: {{ formatDate(period.preference_deadline) }}
						</div>
					</div>

					<!-- Month Navigation -->
					<div class="flex items-center justify-between px-2">
						<div class="text-base font-semibold text-gray-800">
							{{ period.year }}{{ __("年") }}{{ period.month }}{{ __("月") }}
						</div>
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
							<div
								v-if="day.empty"
								class="aspect-square"
							/>
							<button
								v-else
								@click="toggleDate(day)"
								:class="[
									'aspect-square rounded-lg flex flex-col items-center justify-center text-sm relative transition-all',
									getDayClasses(day),
								]"
								:disabled="day.isHoliday && !day.isWeeklyOff"
							>
								<span :class="getDayNumberClasses(day)">{{ day.date }}</span>
								<span
									v-if="getSelectedSlot(day)"
									class="text-[8px] leading-tight mt-0.5 truncate max-w-full px-0.5"
									:class="day.isSelected ? 'text-white' : 'text-gray-400'"
								>
									{{ getSelectedSlot(day) }}
								</span>
								<span
									v-if="day.holidayName && !day.isWeeklyOff"
									class="text-[7px] text-red-400 leading-tight truncate max-w-full px-0.5"
								>
									{{ day.holidayName }}
								</span>
							</button>
						</template>
					</div>

					<!-- Shift Slot Selector Modal -->
					<ion-modal
						:is-open="showSlotSelector"
						@didDismiss="showSlotSelector = false"
						:initial-breakpoint="0.5"
						:breakpoints="[0, 0.5, 0.75]"
					>
						<div class="p-4 space-y-3">
							<div class="text-base font-semibold text-gray-800 text-center">
								{{ selectedDay ? `${period.month}/${selectedDay.date}` : "" }} - {{ __("Select Shift") }}
							</div>
							<div class="space-y-2">
								<button
									v-for="slot in shiftSlots.data || []"
									:key="slot.name"
									@click="selectSlot(slot)"
									class="w-full flex items-center justify-between p-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition"
								>
									<div class="flex items-center gap-2">
										<span
											class="w-3 h-3 rounded-full"
											:style="{ backgroundColor: slot.color || '#6B7280' }"
										/>
										<span class="font-medium text-gray-800">{{ slot.slot_name }}</span>
									</div>
									<span class="text-sm text-gray-500">
										{{ formatTime(slot.start_time) }} - {{ formatTime(slot.end_time) }}
									</span>
								</button>

								<button
									@click="showCustomTime = true"
									class="w-full flex items-center justify-center p-3 rounded-lg border border-dashed border-gray-300 text-gray-500 hover:bg-gray-50 transition"
								>
									{{ __("Custom Time") }}
								</button>

								<div v-if="showCustomTime" class="space-y-2 p-3 bg-gray-50 rounded-lg">
									<div class="flex gap-2">
										<div class="flex-1">
											<label class="text-xs text-gray-500">{{ __("Start") }}</label>
											<input
												v-model="customStart"
												type="time"
												class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
											/>
										</div>
										<div class="flex-1">
											<label class="text-xs text-gray-500">{{ __("End") }}</label>
											<input
												v-model="customEnd"
												type="time"
												class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
											/>
										</div>
									</div>
									<Button
										@click="selectCustomTime"
										variant="solid"
										class="w-full py-2"
										:disabled="!customStart || !customEnd"
									>
										{{ __("Confirm") }}
									</Button>
								</div>

								<button
									v-if="isDateSelected(selectedDay)"
									@click="removeDate(selectedDay)"
									class="w-full flex items-center justify-center p-3 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
								>
									{{ __("Remove") }}
								</button>
							</div>
						</div>
					</ion-modal>

					<!-- Notes -->
					<div class="space-y-1">
						<label class="text-sm font-medium text-gray-700">{{ __("Notes") }}</label>
						<textarea
							v-model="notes"
							:placeholder="__('Any special requests or notes...')"
							class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
							rows="2"
						/>
					</div>

					<!-- Summary -->
					<div class="bg-gray-50 rounded-lg p-3">
						<div class="text-sm font-medium text-gray-700 mb-2">
							{{ __("Selected") }}: {{ selectedDates.length }} {{ __("days") }}
						</div>
						<div class="flex flex-wrap gap-1">
							<span
								v-for="sel in selectedDates"
								:key="sel.date"
								class="inline-flex items-center px-2 py-1 rounded-md text-xs bg-blue-100 text-blue-700"
							>
								{{ formatFullDate(sel.date) }}
								<span class="ml-1 text-blue-500">{{ sel.slotName || __("Custom") }}</span>
							</span>
						</div>
					</div>

					<!-- Submit Button -->
					<Button
						@click="submitPreference"
						variant="solid"
						class="py-4 text-base w-full"
						:loading="submitting"
						:disabled="selectedDates.length === 0"
					>
						{{ existingPref ? __("Update Preference") : __("Submit Preference") }}
					</Button>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ref, computed, inject, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { createResource, Button } from "frappe-ui"
import { IonModal } from "@ionic/vue"
import BaseLayout from "@/components/BaseLayout.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const route = useRoute()
const router = useRouter()

const periodId = computed(() => route.params.periodId)
const showSlotSelector = ref(false)
const showCustomTime = ref(false)
const selectedDay = ref(null)
const customStart = ref("")
const customEnd = ref("")
const notes = ref("")
const submitting = ref(false)
const existingPref = ref(null)
const selections = ref({})

const weekdayHeaders = ["日", "月", "火", "水", "木", "金", "土"]

const periodResource = createResource({
	url: "work_roster.api.preference.get_current_period",
	auto: false,
})

const period = computed(() => {
	if (!periodResource.data) return null
	return periodResource.data.find((p) => p.name === periodId.value) || periodResource.data[0]
})

const shiftSlots = createResource({
	url: "work_roster.api.preference.get_shift_slots",
	auto: true,
	cache: "wr:shift_slots",
})

const existingPrefResource = createResource({
	url: "work_roster.api.preference.get_my_preference",
	auto: false,
})

const holidaysResource = createResource({
	url: "work_roster.api.schedule.get_holidays",
	auto: false,
})

onMounted(() => {
	periodResource.fetch()
})

watch(period, (p) => {
	if (p) {
		existingPrefResource.fetch({ params: { wr_period: p.name } })
		if (p.holiday_list) {
			holidaysResource.fetch({
				params: { holiday_list: p.holiday_list, month: p.month, year: p.year },
			})
		}
	}
})

watch(
	() => existingPrefResource.data,
	(data) => {
		if (data) {
			existingPref.value = data
			notes.value = data.notes || ""
			const newSelections = {}
			for (const d of data.details || []) {
				const dateStr = typeof d.date === "string" ? d.date : dayjs(d.date).format("YYYY-MM-DD")
				newSelections[dateStr] = {
					wr_shift_slot: d.wr_shift_slot,
					slotName: d.wr_shift_slot || __("Custom"),
					custom_start_time: d.custom_start_time,
					custom_end_time: d.custom_end_time,
					is_custom: d.is_custom,
				}
			}
			selections.value = newSelections
		}
	}
)

const holidays = computed(() => {
	const map = {}
	for (const h of holidaysResource.data || []) {
		const d = typeof h.holiday_date === "string" ? h.holiday_date : dayjs(h.holiday_date).format("YYYY-MM-DD")
		map[d] = { description: h.description, weekly_off: h.weekly_off }
	}
	return map
})

const calendarDays = computed(() => {
	if (!period.value) return []

	const year = period.value.year
	const month = period.value.month
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
		const holiday = holidays.value[dateStr]

		days.push({
			date: d,
			dateStr,
			weekday,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isHoliday: !!holiday && !holiday.weekly_off,
			isWeeklyOff: !!holiday?.weekly_off,
			holidayName: holiday?.description || "",
			isSelected: !!selections.value[dateStr],
		})
	}

	return days
})

const selectedDates = computed(() => {
	return Object.entries(selections.value).map(([dateStr, sel]) => ({
		date: dateStr,
		...sel,
	})).sort((a, b) => a.date.localeCompare(b.date))
})

function getDayClasses(day) {
	if (day.isSelected) return "bg-blue-600 text-white shadow-sm"
	if (day.isHoliday) return "bg-red-50 text-red-300"
	if (day.isSunday) return "bg-red-50/50"
	if (day.isSaturday) return "bg-blue-50/50"
	return "bg-white hover:bg-gray-50 border border-gray-100"
}

function getDayNumberClasses(day) {
	if (day.isSelected) return "font-semibold"
	if (day.isHoliday || day.isSunday) return "text-red-500"
	if (day.isSaturday) return "text-blue-500"
	return "text-gray-800"
}

function getSelectedSlot(day) {
	if (!day.dateStr) return ""
	const sel = selections.value[day.dateStr]
	return sel?.slotName || ""
}

function isDateSelected(day) {
	return day && !!selections.value[day.dateStr]
}

function toggleDate(day) {
	if (day.isHoliday && !day.isWeeklyOff) return
	selectedDay.value = day
	showCustomTime.value = false
	customStart.value = ""
	customEnd.value = ""
	showSlotSelector.value = true
}

function selectSlot(slot) {
	if (!selectedDay.value) return
	selections.value[selectedDay.value.dateStr] = {
		wr_shift_slot: slot.name,
		slotName: slot.slot_name,
		custom_start_time: null,
		custom_end_time: null,
		is_custom: 0,
	}
	showSlotSelector.value = false
}

function selectCustomTime() {
	if (!selectedDay.value || !customStart.value || !customEnd.value) return
	selections.value[selectedDay.value.dateStr] = {
		wr_shift_slot: null,
		slotName: `${customStart.value}-${customEnd.value}`,
		custom_start_time: customStart.value,
		custom_end_time: customEnd.value,
		is_custom: 1,
	}
	showSlotSelector.value = false
}

function removeDate(day) {
	if (!day) return
	delete selections.value[day.dateStr]
	showSlotSelector.value = false
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	return dayjs(dateStr).format("M/D (ddd)")
}

function formatFullDate(dateStr) {
	if (!dateStr) return ""
	return dayjs(dateStr).format("M/D")
}

function formatTime(time) {
	if (!time) return ""
	return time.substring(0, 5)
}

async function submitPreference() {
	if (!period.value || selectedDates.value.length === 0) return
	submitting.value = true

	const details = selectedDates.value.map((sel) => ({
		date: sel.date,
		wr_shift_slot: sel.wr_shift_slot,
		custom_start_time: sel.custom_start_time,
		custom_end_time: sel.custom_end_time,
		is_custom: sel.is_custom || 0,
	}))

	try {
		const submitResource = createResource({
			url: "work_roster.api.preference.submit_preference",
		})
		await submitResource.fetch({
			params: {
				wr_period: period.value.name,
				details: JSON.stringify(details),
				notes: notes.value,
			},
		})
		router.push("/dashboard/work-roster")
	} catch (e) {
		console.error("Failed to submit preference:", e)
	} finally {
		submitting.value = false
	}
}
</script>
