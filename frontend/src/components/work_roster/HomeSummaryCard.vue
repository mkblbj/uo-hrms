<template>
	<section class="roster-section">
		<div class="roster-section-header">
			<div>
				<h3>{{ t("title") }}</h3>
				<p>{{ t("subtitle") }}</p>
			</div>
			<router-link to="/dashboard/work-roster" v-slot="{ navigate }">
				<button type="button" class="roster-view-button" @click="navigate">
					<span>{{ t("viewAll") }}</span>
					<FeatherIcon name="chevron-right" class="h-3.5 w-3.5" />
				</button>
			</router-link>
		</div>

		<div v-if="summaryResource.loading" class="roster-card-grid">
			<div class="roster-card is-loading"></div>
			<div class="roster-card is-loading"></div>
		</div>

		<div v-else-if="summaryResource.data?.error === 'no_employee'" class="roster-empty-warning">
			{{ t("noEmployee") }}
		</div>

		<div v-else class="roster-card-grid">
			<article class="roster-card">
				<div class="roster-card-label">{{ t("todayShift") }}</div>
				<template v-if="summaryResource.data?.today_entry">
					<strong class="roster-card-title">
						{{ summaryResource.data.today_entry.shift_label || t("scheduled") }}
					</strong>
					<span class="roster-card-time">
						{{ summaryResource.data.today_entry.scheduled_time || t("customTime") }}
					</span>
					<span class="roster-card-meta">
						{{ departmentLabel(summaryResource.data.today_entry.department_category) }}
					</span>
				</template>
				<template v-else>
					<strong class="roster-card-title">{{ t("todayEmpty") }}</strong>
					<span class="roster-card-meta">{{ t("todayEmptyHint") }}</span>
				</template>
			</article>

			<article class="roster-card">
				<div class="roster-card-label">{{ t("nextShift") }}</div>
				<template v-if="summaryResource.data?.next_entry">
					<span class="roster-card-date">{{
						formatDate(summaryResource.data.next_entry.date)
					}}</span>
					<strong class="roster-card-title">
						{{ summaryResource.data.next_entry.shift_label || t("scheduled") }}
					</strong>
					<span class="roster-card-time">
						{{ summaryResource.data.next_entry.scheduled_time || t("customTime") }}
					</span>
					<span class="roster-card-meta">
						{{ departmentLabel(summaryResource.data.next_entry.department_category) }}
					</span>
				</template>
				<template v-else>
					<strong class="roster-card-title">{{ t("nextEmpty") }}</strong>
					<span class="roster-card-meta">{{ t("nextEmptyHint") }}</span>
				</template>
			</article>
		</div>
	</section>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource, FeatherIcon } from "frappe-ui"
import { getRosterEmptyCopy, resolveHomeLanguage } from "@/utils/homeExperience"

const props = defineProps({
	lang: {
		type: String,
		default: null,
	},
})

const dayjs = inject("$dayjs")
const __ = inject("$translate")
const currentLanguage = computed(() =>
	resolveHomeLanguage(props.lang ? { lang: props.lang } : window.frappe?.boot)
)

const labels = {
	title: { zh: "排班案内", ja: "シフト案内", en: "Roster Guide" },
	subtitle: { zh: "今日与下个班次", ja: "本日と次回のシフト", en: "Today and next shift" },
	viewAll: { zh: "全部", ja: "すべて", en: "All" },
	noEmployee: {
		zh: "未找到当前账号对应的员工档案",
		ja: "現在のアカウントに対応する従業員情報がありません",
		en: "No employee record linked to this account",
	},
	todayShift: { zh: "今日", ja: "本日", en: "Today" },
	nextShift: { zh: "下次", ja: "次回", en: "Next" },
	scheduled: { zh: "已排班", ja: "シフトあり", en: "Scheduled" },
	customTime: { zh: "自定义时段", ja: "カスタム時間", en: "Custom Time" },
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

function t(key) {
	if (
		key === "todayEmpty" ||
		key === "todayEmptyHint" ||
		key === "nextEmpty" ||
		key === "nextEmptyHint"
	) {
		const emptyCopy = getRosterEmptyCopy(currentLanguage.value)
		return {
			todayEmpty: emptyCopy.today,
			todayEmptyHint: emptyCopy.todayHint,
			nextEmpty: emptyCopy.next,
			nextEmptyHint: emptyCopy.nextHint,
		}[key]
	}

	return labels[key]?.[currentLanguage.value] || labels[key]?.zh || __(key)
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	const lang = currentLanguage.value
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

<style scoped>
.roster-section {
	display: grid;
	gap: 12px;
}

.roster-section-header {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 12px;
	padding: 0 2px;
}

.roster-section-header h3 {
	margin: 0;
	font-size: 16px;
	line-height: 1.2;
	font-weight: 900;
	color: var(--h-fg-primary);
}

.roster-section-header p {
	margin: 3px 0 0;
	font-size: 12px;
	font-weight: 700;
	color: var(--h-fg-secondary);
}

.roster-view-button {
	display: inline-flex;
	align-items: center;
	gap: 2px;
	border: 1px solid var(--h-bd-subtle);
	border-radius: 999px;
	background: var(--h-bg-card);
	padding: 7px 10px;
	font-size: 12px;
	line-height: 1;
	font-weight: 800;
	color: var(--h-fg-primary);
}

.roster-card-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 10px;
}

.roster-card {
	display: flex;
	flex-direction: column;
	min-height: 126px;
	border: 1px solid var(--h-bd-subtle);
	border-radius: 18px;
	background: var(--h-bg-card);
	padding: 14px;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 18px rgba(15, 23, 42, 0.04);
}

.roster-card.is-loading {
	background: linear-gradient(90deg, #ffffff 0%, #f8fafc 50%, #ffffff 100%);
	background-size: 200% 100%;
	animation: roster-loading 1.2s ease-in-out infinite;
}

.roster-card-label,
.roster-card-date {
	font-size: 11px;
	line-height: 1.2;
	font-weight: 900;
	color: var(--h-fg-secondary);
}

.roster-card-title {
	display: block;
	margin-top: 12px;
	font-size: 19px;
	line-height: 1.15;
	font-weight: 900;
	color: var(--h-fg-primary);
}

.roster-card-time {
	display: block;
	margin-top: 10px;
	font-size: 13px;
	line-height: 1.2;
	font-weight: 900;
	color: var(--h-summary-shift-fg);
}

.roster-card-meta {
	display: block;
	margin-top: auto;
	padding-top: 10px;
	font-size: 11px;
	line-height: 1.25;
	font-weight: 700;
	color: var(--h-fg-secondary);
}

.roster-empty-warning {
	border: 1px solid var(--h-summary-warn-bd);
	border-radius: 18px;
	background: var(--h-summary-warn-bg);
	padding: 14px;
	font-size: 13px;
	font-weight: 700;
	color: var(--h-summary-warn-fg);
}

@keyframes roster-loading {
	from {
		background-position: 100% 0;
	}

	to {
		background-position: -100% 0;
	}
}
</style>
