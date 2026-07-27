<template>
	<BaseLayout :pageTitle="labels.pageTitle">
		<template #body>
			<main class="roster-page">
				<RosterPreferenceBanner :notice="currentData?.preference_notice" :labels="labels" />
				<RosterViewTabs v-model="activeScope" :labels="labels" />
				<RosterMonthHeader
					:year="currentYear"
					:month="currentMonth"
					:month-title="monthTitle"
					:department-category="departmentCategory"
					:published="Boolean(currentData?.period)"
					:labels="labels"
					@previous="moveMonth(-1)"
					@next="moveMonth(1)"
				/>

				<section v-if="isInitialLoading" class="roster-state roster-skeleton" aria-live="polite">
					<span>{{ labels.loading }}</span>
					<div v-for="index in 35" :key="index" aria-hidden="true"></div>
				</section>

				<section
					v-else-if="currentData?.error === 'no_employee'"
					class="roster-state"
					role="status"
				>
					<strong>{{ labels.noEmployee }}</strong>
				</section>

				<section v-else-if="currentError" class="roster-state error" role="alert">
					<strong>{{ labels.loadError }}</strong>
					<button type="button" @click="retry">
						{{ labels.retry }}
					</button>
				</section>

				<template v-else-if="currentData">
					<p v-if="!currentData.period" class="period-missing" role="status">
						{{ labels.periodMissing }}
					</p>
					<RosterMonthCalendar
						v-if="calendarCells.length"
						ref="calendarRef"
						:cells="calendarCells"
						:scope="activeScope"
						:department-category="departmentCategory"
						:weekday-labels="weekdayLabels"
						:labels="labels"
						@select-day="openDay"
					/>
				</template>

				<RosterDaySheet
					:day="selectedCell"
					:scope="activeScope"
					:department-category="departmentCategory"
					:labels="labels"
					@close="closeDay"
				/>
			</main>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { useRoute } from "vue-router"

import BaseLayout from "@/components/BaseLayout.vue"
import RosterDaySheet from "@/components/work_roster/RosterDaySheet.vue"
import RosterMonthCalendar from "@/components/work_roster/RosterMonthCalendar.vue"
import RosterMonthHeader from "@/components/work_roster/RosterMonthHeader.vue"
import RosterPreferenceBanner from "@/components/work_roster/RosterPreferenceBanner.vue"
import RosterViewTabs from "@/components/work_roster/RosterViewTabs.vue"
import {
	addRosterMonth,
	buildRosterCalendarCells,
	createRosterRequestGate,
	getRosterCacheKey,
	getRosterCopy,
	normalizeRosterLanguage,
	resolveRosterFallbackMonth,
	resolveRosterInitialState,
} from "@/utils/rosterCalendar"

const LABEL_KEYS = [
	"pageTitle",
	"viewSelector",
	"myShift",
	"departmentShift",
	"submitPreference",
	"editPreference",
	"submitted",
	"scheduling",
	"deadline",
	"previousMonth",
	"nextMonth",
	"published",
	"periodMissing",
	"departmentOffice",
	"departmentProduction",
	"holiday",
	"sale",
	"bigSale",
	"saturday",
	"sunday",
	"actualShort",
	"equivalentShort",
	"scheduledPeople",
	"equivalentPeople",
	"rest",
	"emptyShort",
	"emptyDay",
	"customTime",
	"loading",
	"loadError",
	"retry",
	"noEmployee",
	"close",
	"shiftLabel",
	"scheduledTime",
]

const route = useRoute()
const initialState = resolveRosterInitialState({
	now: new Date(),
	query: route.query,
})
const activeScope = ref(initialState.scope)
const currentYear = ref(initialState.year)
const currentMonth = ref(initialState.month)
const selectedCell = ref(null)
const calendarRef = ref(null)
const cache = reactive(new Map())
const errors = reactive(new Map())
const loadingKeys = reactive(new Set())
const requestGate = createRosterRequestGate()
let hasEntered = false

const rosterResource = createResource({
	url: "work_roster.api.schedule.get_mobile_roster_calendar",
	auto: false,
})
const legacyPeriodResource = createResource({
	url: "work_roster.api.schedule.resolve_mobile_roster_period",
	auto: false,
})

const language = computed(() => normalizeRosterLanguage(globalThis.frappe?.boot?.lang))
const labels = computed(() =>
	Object.fromEntries(LABEL_KEYS.map((key) => [key, getRosterCopy(key, language.value)]))
)
const currentKey = computed(() =>
	getRosterCacheKey(activeScope.value, currentYear.value, currentMonth.value)
)
const currentData = computed(() => cache.get(currentKey.value) || null)
const currentError = computed(() => errors.get(currentKey.value) || null)
const isInitialLoading = computed(() => !currentData.value && loadingKeys.has(currentKey.value))
const departmentCategory = computed(() => currentData.value?.department_category || "")
const today = localDateKey(new Date())
const calendarCells = computed(() => {
	if (!currentData.value || currentData.value.error) return []
	return buildRosterCalendarCells({
		year: currentYear.value,
		month: currentMonth.value,
		days: currentData.value.days || [],
		holidays: currentData.value.holidays || [],
		events: currentData.value.events || [],
		today,
	})
})
const weekdayLabels = computed(() => {
	if (language.value === "ja") {
		return ["日", "月", "火", "水", "木", "金", "土"]
	}
	if (language.value === "en") {
		return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
	}
	return ["日", "一", "二", "三", "四", "五", "六"]
})
const monthTitle = computed(() => {
	if (language.value === "en") {
		return new Intl.DateTimeFormat("en", {
			year: "numeric",
			month: "long",
		}).format(new Date(currentYear.value, currentMonth.value - 1, 1))
	}
	return `${currentYear.value}年${currentMonth.value}月`
})

function localDateKey(date) {
	const year = date.getFullYear()
	const month = String(date.getMonth() + 1).padStart(2, "0")
	const day = String(date.getDate()).padStart(2, "0")
	return `${year}-${month}-${day}`
}

async function loadCurrentMonth({ initial = false, force = false } = {}) {
	const scope = activeScope.value
	const year = currentYear.value
	const month = currentMonth.value
	const key = getRosterCacheKey(scope, year, month)
	if (!force && cache.has(key)) return cache.get(key)

	const token = requestGate.begin()
	errors.delete(key)
	loadingKeys.add(key)
	try {
		const fetched = await rosterResource.fetch({
			year,
			month,
			scope,
		})
		const response = fetched ?? rosterResource.data
		if (!requestGate.isLatest(token)) return null
		cache.set(key, response)
		const fallback = resolveRosterFallbackMonth({
			requested: { year, month },
			response,
			initial,
		})
		if (fallback) {
			currentYear.value = fallback.year
			currentMonth.value = fallback.month
			return loadCurrentMonth({ initial: false })
		}
		return response
	} catch (error) {
		if (requestGate.isLatest(token)) {
			errors.set(key, error)
		}
		return null
	} finally {
		loadingKeys.delete(key)
	}
}

function moveMonth(delta) {
	closeDay({ restoreFocus: false })
	const target = addRosterMonth({ year: currentYear.value, month: currentMonth.value }, delta)
	currentYear.value = target.year
	currentMonth.value = target.month
	loadCurrentMonth()
}

function openDay(cell) {
	selectedCell.value = cell
}

async function closeDay({ restoreFocus = true } = {}) {
	const previousDate = selectedCell.value?.dateStr
	selectedCell.value = null
	if (restoreFocus && previousDate) {
		await nextTick()
		calendarRef.value?.focusDate(previousDate)
	}
}

function retry() {
	loadCurrentMonth({ force: true })
}

async function applyLegacyPeriod() {
	if (!initialState.legacyPeriod) return
	try {
		const fetched = await legacyPeriodResource.fetch({
			wr_period: initialState.legacyPeriod,
		})
		const target = fetched ?? legacyPeriodResource.data
		if (target?.year && target?.month) {
			currentYear.value = Number(target.year)
			currentMonth.value = Number(target.month)
		}
	} catch {
		// An inaccessible or obsolete period safely falls back to the current month.
	}
}

watch(activeScope, () => {
	closeDay({ restoreFocus: false })
	loadCurrentMonth()
})

onIonViewWillEnter(async () => {
	const requestedScope = route.query.view === "department" ? "department" : "mine"
	if (!hasEntered) {
		hasEntered = true
		activeScope.value = requestedScope
		await applyLegacyPeriod()
		await loadCurrentMonth({ initial: true })
		return
	}

	if (activeScope.value !== requestedScope) {
		activeScope.value = requestedScope
		return
	}

	const hasCachedMonth = cache.has(currentKey.value)
	await loadCurrentMonth()
	if (hasCachedMonth) {
		loadCurrentMonth({ force: true })
	}
})
</script>

<style scoped>
.roster-page {
	display: grid;
	width: 100%;
	max-width: 520px;
	margin: 0 auto;
	padding: 12px 12px calc(96px + env(safe-area-inset-bottom));
	gap: 12px;
	overflow-x: hidden;
	color: var(--h-fg-primary, #0a0a0a);
	background: var(--h-bg-page, #f1eee7);
}

.roster-state {
	display: grid;
	min-height: 200px;
	place-items: center;
	padding: 24px 16px;
	color: var(--h-fg-secondary, #64748b);
	text-align: center;
	background: var(--h-bg-card, #ffffff);
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 16px;
}

.roster-state.error {
	gap: 12px;
	align-content: center;
}

.roster-state.error button {
	min-width: 96px;
	min-height: 40px;
	padding: 8px 14px;
	color: var(--h-fg-on-dark, #ffffff);
	font-size: 13px;
	font-weight: 700;
	background: var(--h-tab-active, #2563eb);
	border: 0;
	border-radius: 10px;
}

.roster-skeleton {
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 3px;
	padding: 8px;
}

.roster-skeleton span {
	grid-column: 1 / -1;
	padding: 12px;
	font-size: 13px;
}

.roster-skeleton div {
	width: 100%;
	aspect-ratio: 0.78;
	background: var(--h-bg-card-inner, #faf8f2);
	border-radius: 8px;
	animation: roster-pulse 1.25s ease-in-out infinite alternate;
}

.period-missing {
	margin: 0;
	padding: 9px 12px;
	color: var(--h-fg-secondary, #64748b);
	font-size: 12px;
	text-align: center;
	background: var(--h-bg-card, #ffffff);
	border: 1px dashed var(--h-bd-default, #e3dfd4);
	border-radius: 12px;
}

@keyframes roster-pulse {
	from {
		opacity: 0.55;
	}
	to {
		opacity: 1;
	}
}

@media (max-width: 340px) {
	.roster-page {
		padding-right: 8px;
		padding-left: 8px;
		gap: 10px;
	}
}

@media (prefers-reduced-motion: reduce) {
	.roster-skeleton div {
		animation: none;
	}
}
</style>
