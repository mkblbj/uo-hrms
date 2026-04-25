<template>
	<BaseLayout :pageTitle="t('pageTitle')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 space-y-4">
				<div v-if="periodResource.loading" class="text-center py-10">
					<div class="text-gray-400">{{ t("loading") }}</div>
				</div>

				<template v-else-if="period">
					<div class="text-center">
						<div class="text-lg font-semibold text-gray-800">{{ period.title }}</div>
						<div class="text-sm text-gray-500 mt-1">
							{{ t("deadline") }}：{{ formatDate(period.preference_deadline) }}
						</div>
					</div>

					<!-- Month Navigation -->
					<div class="flex items-center justify-between px-2">
						<div class="text-base font-semibold text-gray-800">
							{{ formatMonthTitle(period.year, period.month) }}
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
						:initial-breakpoint="0.82"
						:breakpoints="[0, 0.5, 0.82, 1]"
					>
						<div class="p-4 space-y-3 overflow-y-auto max-h-[85vh] pb-8">
							<div class="text-base font-semibold text-gray-800 text-center">
								{{ selectedDay ? `${period.month}/${selectedDay.date}` : "" }} - {{ t("chooseShift") }}
							</div>
							<div class="space-y-2">
								<button
									@click="showCustomTime = !showCustomTime"
									class="w-full flex items-center justify-center p-3 rounded-lg border border-dashed border-blue-300 text-blue-600 hover:bg-blue-50 transition"
								>
									{{ showCustomTime ? t("hideCustomTime") : t("useCustomTime") }}
								</button>

								<div v-if="showCustomTime" class="space-y-2 p-3 bg-gray-50 rounded-lg">
									<div class="flex gap-2">
										<div class="flex-1">
											<label class="text-xs text-gray-500">{{ t("startTime") }}</label>
											<input
												v-model="customStart"
												type="time"
												class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
											/>
										</div>
										<div class="flex-1">
											<label class="text-xs text-gray-500">{{ t("endTime") }}</label>
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
										{{ t("saveCustomTime") }}
									</Button>
								</div>

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
									v-if="isDateSelected(selectedDay)"
									@click="removeDate(selectedDay)"
									class="w-full flex items-center justify-center p-3 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
								>
									{{ t("removeSelection") }}
								</button>
							</div>
						</div>
					</ion-modal>

					<!-- Notes -->
					<div class="space-y-1">
						<label class="text-sm font-medium text-gray-700">{{ t("notes") }}</label>
						<textarea
							v-model="notes"
							:placeholder="t('notesPlaceholder')"
							class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
							rows="2"
						/>
					</div>

					<!-- Summary -->
					<div class="bg-gray-50 rounded-lg p-3">
						<div class="text-sm font-medium text-gray-700 mb-2">
							{{ t("selectedDays", { count: selectedDates.length }) }}
						</div>
						<div class="flex flex-wrap gap-1">
							<span
								v-for="sel in selectedDates"
								:key="sel.date"
								class="inline-flex items-center px-2 py-1 rounded-md text-xs bg-blue-100 text-blue-700"
							>
								{{ formatFullDate(sel.date) }}
								<span class="ml-1 text-blue-500">{{ sel.slotName || t("custom") }}</span>
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
						{{ existingPref ? t("updatePreference") : t("submitPreference") }}
					</Button>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { ref, computed, inject, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { createResource, Button, toast } from "frappe-ui"
import { IonModal, onIonViewWillEnter } from "@ionic/vue"
import BaseLayout from "@/components/BaseLayout.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
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

const labels = {
	pageTitle: { zh: "提交排班意愿", ja: "シフト希望提出", en: "Submit Roster Preference" },
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	deadline: { zh: "截止时间", ja: "締切", en: "Deadline" },
	chooseShift: { zh: "选择班次", ja: "シフトを選択", en: "Choose Shift" },
	hideCustomTime: { zh: "收起自定义时间", ja: "カスタム時間を閉じる", en: "Hide Custom Time" },
	useCustomTime: { zh: "使用自定义时间", ja: "カスタム時間を使う", en: "Use Custom Time" },
	startTime: { zh: "开始时间", ja: "開始時間", en: "Start Time" },
	endTime: { zh: "结束时间", ja: "終了時間", en: "End Time" },
	saveCustomTime: { zh: "保存自定义时间", ja: "カスタム時間を保存", en: "Save Custom Time" },
	removeSelection: { zh: "移除当天选择", ja: "当日の選択を削除", en: "Remove Selection" },
	notes: { zh: "备注", ja: "備考", en: "Notes" },
	notesPlaceholder: { zh: "可填写特殊说明，例如希望连班、只想上半天等", ja: "連勤希望や半日希望などの補足を入力できます", en: "Add notes such as back-to-back shifts or half-day preference" },
	selectedDays: { zh: "已选择：{count} 天", ja: "{count} 日を選択済み", en: "{count} day(s) selected" },
	custom: { zh: "自定义", ja: "カスタム", en: "Custom" },
	updatePreference: { zh: "更新意愿", ja: "希望を更新", en: "Update Preference" },
	submitPreference: { zh: "提交意愿", ja: "希望を提出", en: "Submit Preference" },
	timeOrderError: { zh: "结束时间必须晚于开始时间", ja: "終了時間は開始時間より後である必要があります", en: "End time must be later than start time" },
	submitSuccess: { zh: "排班意愿提交成功", ja: "シフト希望を提出しました", en: "Roster preference submitted" },
	submitFailed: { zh: "提交失败，请稍后重试", ja: "提出に失敗しました。しばらくしてから再試行してください", en: "Submission failed. Please try again later." },
}
const weekdayHeaderMap = {
	zh: ["日", "一", "二", "三", "四", "五", "六"],
	ja: ["日", "月", "火", "水", "木", "金", "土"],
	en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
}
const weekdayHeaders = computed(() => weekdayHeaderMap[getLang()] || weekdayHeaderMap.zh)

function getLang() {
	return frappe?.boot?.lang || "zh"
}

function t(key, params = null) {
	const text = labels[key]?.[getLang()] || labels[key]?.zh || __(key)
	if (!params) return text
	return text.replace(/\{(\w+)\}/g, (_, name) => `${params[name] ?? ""}`)
}

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
	auto: false,
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

onIonViewWillEnter(() => {
	periodResource.fetch()
})

watch(period, (p) => {
	if (p) {
		existingPrefResource.fetch({ wr_period: p.name })
		shiftSlots.fetch({ department_category: p.department_category })
		if (p.holiday_list) {
			holidaysResource.fetch({ holiday_list: p.holiday_list, month: p.month, year: p.year })
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
					slotName: d.wr_shift_slot || t("custom"),
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
	selectedDay.value = day
	const existingSelection = selections.value[day.dateStr]
	showCustomTime.value = !!existingSelection?.is_custom
	customStart.value = existingSelection?.custom_start_time?.substring(0, 5) || ""
	customEnd.value = existingSelection?.custom_end_time?.substring(0, 5) || ""
	showSlotSelector.value = true
}

function selectSlot(slot) {
	if (!selectedDay.value) return
	selections.value = {
		...selections.value,
		[selectedDay.value.dateStr]: {
			wr_shift_slot: slot.name,
			slotName: slot.slot_name,
			custom_start_time: null,
			custom_end_time: null,
			is_custom: 0,
		},
	}
	showSlotSelector.value = false
}

function selectCustomTime() {
	if (!selectedDay.value || !customStart.value || !customEnd.value) return
	if (customEnd.value <= customStart.value) {
		toast({
			text: t("timeOrderError"),
			position: "bottom",
			icon: "x-circle",
			iconClasses: "text-red-500",
		})
		return
	}

	selections.value = {
		...selections.value,
		[selectedDay.value.dateStr]: {
			wr_shift_slot: null,
			slotName: `${customStart.value}-${customEnd.value}`,
			custom_start_time: normalizeTime(customStart.value),
			custom_end_time: normalizeTime(customEnd.value),
			is_custom: 1,
		},
	}
	showSlotSelector.value = false
}

function removeDate(day) {
	if (!day) return
	const newSelections = { ...selections.value }
	delete newSelections[day.dateStr]
	selections.value = newSelections
	showSlotSelector.value = false
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

function formatMonthTitle(year, month) {
	if (getLang() === "en") {
		return dayjs(`${year}-${String(month).padStart(2, "0")}-01`).format("MMMM YYYY")
	}
	return `${year}年${month}月`
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
		const result = await submitResource.fetch({
			wr_period: period.value.name,
			details: JSON.stringify(details),
			notes: notes.value,
		})
		existingPref.value = result
		toast({
			text: t("submitSuccess"),
			position: "bottom",
			icon: "check-circle",
			iconClasses: "text-green-600",
		})
		router.push("/dashboard/work-roster")
	} catch (e) {
		console.error("Failed to submit preference:", e)
		toast({
			text: e?.messages?.[0] || e?.message || t("submitFailed"),
			position: "bottom",
			icon: "x-circle",
			iconClasses: "text-red-500",
		})
	} finally {
		submitting.value = false
	}
}

function normalizeTime(value) {
	if (!value) return value
	return value.length === 5 ? `${value}:00` : value
}
</script>
