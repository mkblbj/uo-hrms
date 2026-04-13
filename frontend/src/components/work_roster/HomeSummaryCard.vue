<template>
	<div class="space-y-3">
		<div class="flex items-start justify-between gap-3">
			<div>
				<div class="text-lg font-bold text-gray-900">{{ t("title") }}</div>
				<div class="text-sm text-gray-500">{{ t("subtitle") }}</div>
			</div>
			<router-link to="/dashboard/work-roster" v-slot="{ navigate }">
				<button
					@click="navigate"
					class="shrink-0 rounded-full bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-600"
				>
					{{ t("viewAll") }}
				</button>
			</router-link>
		</div>

		<div v-if="summaryResource.loading" class="grid grid-cols-2 gap-3">
			<div class="h-[132px] rounded-2xl bg-white shadow-sm animate-pulse"></div>
			<div class="h-[132px] rounded-2xl bg-white shadow-sm animate-pulse"></div>
		</div>

		<div
			v-else-if="summaryResource.data?.error === 'no_employee'"
			class="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-5 text-sm text-amber-700 shadow-sm"
		>
			{{ t("noEmployee") }}
		</div>

		<div v-else class="grid grid-cols-2 gap-3">
			<div class="rounded-2xl bg-white px-4 py-4 shadow-sm border-l-4 border-blue-500">
				<div class="text-xs font-medium text-blue-600">{{ t("todayShift") }}</div>
				<template v-if="summaryResource.data?.today_entry">
					<div class="mt-3 text-2xl font-bold leading-none text-gray-900">
						{{ summaryResource.data.today_entry.shift_label || t("scheduled") }}
					</div>
					<div class="mt-3 text-sm font-semibold text-blue-700">
						{{ summaryResource.data.today_entry.scheduled_time || t("customTime") }}
					</div>
					<div class="mt-2 text-xs text-gray-500">
						{{ departmentLabel(summaryResource.data.today_entry.department_category) }}
					</div>
				</template>
				<template v-else>
					<div class="mt-3 text-lg font-semibold text-gray-800">{{ t("todayEmpty") }}</div>
					<div class="mt-3 text-sm text-gray-500">{{ t("todayEmptyHint") }}</div>
				</template>
			</div>

			<div class="rounded-2xl bg-white px-4 py-4 shadow-sm border-l-4 border-emerald-500">
				<div class="text-xs font-medium text-emerald-600">{{ t("nextShift") }}</div>
				<template v-if="summaryResource.data?.next_entry">
					<div class="mt-3 text-sm font-semibold text-gray-600">
						{{ formatDate(summaryResource.data.next_entry.date) }}
					</div>
					<div class="mt-2 text-2xl font-bold leading-none text-gray-900">
						{{ summaryResource.data.next_entry.shift_label || t("scheduled") }}
					</div>
					<div class="mt-3 text-sm font-semibold text-emerald-700">
						{{ summaryResource.data.next_entry.scheduled_time || t("customTime") }}
					</div>
					<div class="mt-2 text-xs text-gray-500">
						{{ departmentLabel(summaryResource.data.next_entry.department_category) }}
					</div>
				</template>
				<template v-else>
					<div class="mt-3 text-lg font-semibold text-gray-800">{{ t("nextEmpty") }}</div>
					<div class="mt-3 text-sm text-gray-500">{{ t("nextEmptyHint") }}</div>
				</template>
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource } from "frappe-ui"

const dayjs = inject("$dayjs")
const __ = inject("$translate")

const labels = {
	title: { zh: "排班提醒", ja: "シフト案内", en: "Roster Alerts" },
	subtitle: { zh: "查看今日班次和下一个班次", ja: "本日と次回のシフトを確認", en: "Check today and next shifts" },
	viewAll: { zh: "查看全部", ja: "すべて表示", en: "View All" },
	noEmployee: { zh: "未找到当前账号对应的员工档案", ja: "現在のアカウントに対応する従業員情報がありません", en: "No employee record linked to this account" },
	todayShift: { zh: "今日班次", ja: "本日のシフト", en: "Today's Shift" },
	nextShift: { zh: "下一个班次", ja: "次のシフト", en: "Next Shift" },
	scheduled: { zh: "已排班", ja: "シフトあり", en: "Scheduled" },
	customTime: { zh: "自定义时段", ja: "カスタム時間", en: "Custom Time" },
	todayEmpty: { zh: "今天暂无班次", ja: "本日のシフトはありません", en: "No shift today" },
	todayEmptyHint: { zh: "当前没有已发布的今日排班", ja: "本日公開済みのシフトはありません", en: "No published shift for today" },
	nextEmpty: { zh: "暂无下一个班次", ja: "次のシフトはありません", en: "No next shift" },
	nextEmptyHint: { zh: "还没有后续已发布排班", ja: "今後の公開済みシフトはありません", en: "No upcoming published shift" },
	departmentOffice: { zh: "办公室", ja: "事務所", en: "Office" },
	departmentProduction: { zh: "生产", ja: "生産", en: "Production" },
}

const summaryResource = createResource({
	url: "work_roster.api.schedule.get_home_schedule_summary",
	auto: false,
})

function loadSummary() {
	summaryResource.fetch()
}

function getLang() {
	return frappe?.boot?.lang || "zh"
}

function t(key) {
	return labels[key]?.[getLang()] || labels[key]?.zh || __(key)
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const lang = getLang()
	const weekdayMap = {
		zh: ["日", "一", "二", "三", "四", "五", "六"],
		ja: ["日", "月", "火", "水", "木", "金", "土"],
		en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
	}[lang] || ["日", "一", "二", "三", "四", "五", "六"]
	const date = dayjs(dateStr)
	if (lang === "en") {
		return `${date.format("M/D")} (${weekdayMap[date.day()]})`
	}
	if (lang === "ja") {
		return `${date.format("M/D")}（${weekdayMap[date.day()]}）`
	}
	return `${date.format("M/D")}（周${weekdayMap[date.day()]}）`
}

function departmentLabel(category) {
	if (category === "Office") return t("departmentOffice")
	if (category === "Production") return t("departmentProduction")
	return category || ""
}

onMounted(() => {
	loadSummary()
})

onIonViewWillEnter(() => {
	loadSummary()
})
</script>
