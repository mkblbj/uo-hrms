<template>
	<BaseLayout :pageTitle="t('pageTitle')">
		<template #body>
			<div class="flex flex-col items-center mt-4 mb-7 py-4 px-4 space-y-5">
				<div v-if="dashboardData.loading" class="w-full text-center py-10">
					<div class="text-gray-400">{{ t("loading") }}</div>
				</div>

				<div v-else-if="dashboardData.data?.error === 'no_employee'" class="w-full text-center py-10">
					<div class="text-gray-500">{{ t("noEmployee") }}</div>
				</div>

				<template v-else-if="dashboardData.data">
					<div
						v-for="period in dashboardData.data.periods"
						:key="period.name"
						class="w-full bg-white rounded-xl shadow-sm p-4 border border-gray-100"
					>
						<div class="flex items-center justify-between mb-3">
							<div>
								<div class="text-base font-semibold text-gray-800">{{ period.title }}</div>
								<StatusBadge :status="period.status" />
							</div>
						</div>

						<div v-if="period.status === 'Collecting'" class="space-y-3">
							<div class="text-sm text-gray-600">
								{{ t("deadline") }}：{{ formatDate(period.preference_deadline) }}
							</div>
							<div class="flex items-center gap-2">
								<span
									:class="period.has_preference ? 'text-green-600' : 'text-orange-500'"
									class="text-sm font-medium"
								>
									{{ period.has_preference ? t("submitted") : t("pendingSubmit") }}
								</span>
							</div>
							<router-link
								:to="`/work-roster/preference/${period.name}`"
								v-slot="{ navigate }"
							>
								<Button
									@click="navigate"
									:variant="period.has_preference ? 'subtle' : 'solid'"
									class="py-3 text-sm w-full"
								>
									{{ period.has_preference ? t("editPreference") : t("submitPreference") }}
								</Button>
							</router-link>
						</div>

						<div v-else-if="period.status === 'Published'" class="space-y-3">
							<div v-if="period.upcoming_entries?.length" class="space-y-1.5">
								<div class="text-sm font-medium text-gray-700">{{ t("upcomingShifts") }}</div>
								<div
									v-for="entry in period.upcoming_entries"
									:key="entry.date"
									class="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
								>
									<span class="text-gray-600">{{ formatDate(entry.date) }}</span>
									<span class="font-medium text-gray-800">{{ entry.wr_shift_slot || t("customTime") }}</span>
								</div>
							</div>
							<div class="flex gap-2">
								<router-link
									to="/work-roster/my-schedule"
									v-slot="{ navigate }"
									class="flex-1"
								>
									<Button @click="navigate" variant="subtle" class="py-3 text-sm w-full">
										{{ t("myRoster") }}
									</Button>
								</router-link>
								<router-link
									:to="`/work-roster/department-schedule/${period.name}`"
									v-slot="{ navigate }"
									class="flex-1"
								>
									<Button @click="navigate" variant="outline" class="py-3 text-sm w-full">
										{{ t("departmentRoster") }}
									</Button>
								</router-link>
							</div>
						</div>

						<div v-else-if="period.status === 'Scheduling'" class="text-sm text-gray-500 py-2">
							{{ t("schedulingHint") }}
						</div>
					</div>

					<div v-if="!dashboardData.data.periods?.length" class="w-full text-center py-10">
						<div class="text-gray-400 text-sm">{{ t("emptyPeriods") }}</div>
					</div>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource, Button } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"
import StatusBadge from "@/components/work_roster/StatusBadge.vue"

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const labels = {
	pageTitle: { zh: "排班", ja: "シフト", en: "Roster" },
	loading: { zh: "加载中...", ja: "読み込み中...", en: "Loading..." },
	noEmployee: { zh: "未找到当前账号对应的员工档案", ja: "現在のアカウントに対応する従業員情報がありません", en: "No employee record linked to this account" },
	deadline: { zh: "截止时间", ja: "締切", en: "Deadline" },
	submitted: { zh: "已提交", ja: "提出済み", en: "Submitted" },
	pendingSubmit: { zh: "待提交", ja: "未提出", en: "Pending" },
	editPreference: { zh: "修改意愿", ja: "希望を修正", en: "Edit Preference" },
	submitPreference: { zh: "提交意愿", ja: "希望を提出", en: "Submit Preference" },
	upcomingShifts: { zh: "即将到来的班次", ja: "今後のシフト", en: "Upcoming Shifts" },
	customTime: { zh: "自定义时段", ja: "カスタム時間", en: "Custom Time" },
	myRoster: { zh: "我的排班", ja: "私のシフト", en: "My Roster" },
	departmentRoster: { zh: "部门排班", ja: "部門シフト", en: "Department Roster" },
	schedulingHint: { zh: "排班正在编制中，请稍后查看", ja: "シフトを編成中です。しばらくしてからご確認ください", en: "Roster is being prepared. Please check again later." },
	emptyPeriods: { zh: "当前没有可用的排班周期", ja: "利用可能なシフト期間はありません", en: "No available roster periods" },
}

const dashboardData = createResource({
	url: "work_roster.api.schedule.get_dashboard_data",
	auto: false,
})

function getLang() {
	return frappe?.boot?.lang || "zh"
}

function t(key) {
	return labels[key]?.[getLang()] || labels[key]?.zh || __(key)
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const weekdayMap = {
		zh: ["日", "一", "二", "三", "四", "五", "六"],
		ja: ["日", "月", "火", "水", "木", "金", "土"],
		en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
	}[getLang()] || ["日", "一", "二", "三", "四", "五", "六"]
	const date = dayjs(dateStr)
	if (getLang() === "en") {
		return `${date.format("M/D")} (${weekdayMap[date.day()]})`
	}
	if (getLang() === "ja") {
		return `${date.format("M/D")}（${weekdayMap[date.day()]}）`
	}
	return `${date.format("M/D")}（周${weekdayMap[date.day()]}）`
}

onIonViewWillEnter(() => {
	dashboardData.fetch()
})
</script>
