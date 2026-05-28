<template>
	<div class="attn-root" v-if="isLoading">
		<div class="attn-skeleton" />
	</div>

	<div class="attn-root" v-else>
		<!-- Month switcher + mini overview -->
		<div class="month-bar">
			<button class="nav-btn" @click="prevMonth" :aria-label="t('prev')">
				<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M15 18l-6-6 6-6" />
				</svg>
			</button>
			<div class="month-label-wrap">
				<span class="month-label">{{ monthTitle }}</span>
			</div>
			<button class="nav-btn" @click="nextMonth" :aria-label="t('next')">
				<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M9 18l6-6-6-6" />
				</svg>
			</button>
		</div>

		<!-- 9-chip Legend -->
		<div class="legend">
			<div v-for="item in legendItems" :key="item.key" class="legend-chip">
				<span class="swatch" :class="`sw-${item.key}`" :style="item.style" />
				<span class="legend-text">{{ t(`legend.${item.key}`) }}</span>
			</div>
		</div>

		<!-- Weekday header -->
		<div class="week-header">
			<div
				v-for="(day, idx) in weekdayHeaders"
				:key="idx"
				class="weekday"
				:class="idx === 0 ? 'wd-sun' : idx === 6 ? 'wd-sat' : ''"
			>
				{{ day }}
			</div>
		</div>

		<!-- Calendar grid -->
		<div class="calendar-grid" :style="calendarGridStyle">
			<template v-for="(cell, idx) in calendarCells" :key="cell.key">
				<div v-if="cell.empty" class="cell-blank" />
				<button
					v-else
					class="cell"
					:class="cellClasses(cell)"
					:style="cellStyleFor(cell)"
					@click="openDay(cell)"
				>
					<div class="cell-top">
						<span class="cell-date" :style="{ color: dateColor(cell) }">{{ cell.day }}</span>
						<span
							v-if="showWeekendDot(cell)"
							class="weekend-dot"
							:style="{ background: cell.weekday === 0 ? colors.red : colors.blue }"
						/>
					</div>
					<div class="cell-bottom">
						<span
							v-if="cellBadge(cell)"
							class="cell-badge"
							:style="badgeStyle(cell)"
						>{{ cellBadge(cell) }}</span>
					</div>
				</button>
			</template>
		</div>

		<!-- Month Summary Strip -->
		<div class="detail-strip month-summary-strip">
			<div class="month-summary-head">
				<span class="month-summary-kicker">{{ monthTitle }}</span>
				<strong>{{ t("summary.title") }}</strong>
			</div>
			<div class="month-summary-metrics">
				<div class="month-summary-metric">
					<span>{{ t("summary.totalHours") }}</span>
					<strong>{{ monthSummary.hours }}<small>{{ metaLabels.hours }}</small></strong>
				</div>
				<div class="month-summary-metric">
					<span>{{ t("summary.workDays") }}</span>
					<strong>{{ monthSummary.workDays }}<small>{{ metaLabels.days }}</small></strong>
				</div>
				<div class="month-summary-metric">
					<span>{{ t("summary.avgHours") }}</span>
					<strong>{{ monthSummary.avg }}<small>{{ metaLabels.hours }}</small></strong>
				</div>
			</div>
		</div>

		<!-- Day Dialog -->
		<teleport to="body">
			<div v-if="dialogCell" class="dlg-mask" @click="closeDialog">
				<div class="dlg-card" @click.stop>
					<div class="dlg-header">
						<div>
							<div class="dlg-eyebrow">{{ dialogCell.is_today ? t("detail.today") : t("detail.selected") }}</div>
							<div class="dlg-title">
								{{ currentMonth }}/{{ dialogCell.day }}
								<span
									class="dlg-weekday"
									:style="{ color: dialogCell.weekday === 0 ? colors.red : dialogCell.weekday === 6 ? colors.blue : colors.ink3 }"
								>{{ weekdayHeaders[dialogCell.weekday] }}</span>
							</div>
							<div v-if="dialogCell.holiday" class="dlg-holiday-name">{{ dialogCell.holiday }}</div>
						</div>
						<button class="dlg-close" @click="closeDialog" :aria-label="t('close')">
							<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
								<path d="M6 6l12 12M18 6L6 18" />
							</svg>
						</button>
					</div>

					<div class="dlg-status">
						<div class="dlg-status-text">
							<div class="dlg-eyebrow">{{ t("detail.status") }}</div>
							<div class="dlg-status-label" :style="{ color: statusColor(dialogCell) }">
								{{ statusLabel(dialogCell) }}
								<span
									v-if="dialogCell.is_today && !dialogCell.out_time && isWorkLike(dialogCell)"
									class="ongoing-chip"
								>● {{ t("detail.ongoing") }}</span>
								<span
									v-if="dialogCell.state === 'anomaly' && dialogCell.anomaly_label"
									class="dlg-anomaly-reason"
								>
									{{ dialogCell.anomaly_label }}
								</span>
							</div>
						</div>
						<div class="dlg-status-icon" :style="detailPillStyle(dialogCell)">
							<component :is="StateIcon" :cell="dialogCell" />
						</div>
					</div>

					<div class="dlg-grid" v-if="isAttendanceDetailVisible(dialogCell)">
						<div class="data-cell">
							<div class="dlg-eyebrow">{{ t("detail.in") }}</div>
							<div class="data-value" :style="{ color: colors.green_dk }">{{ dialogCell.in_time || "—:—" }}</div>
						</div>
						<div class="data-cell">
							<div class="dlg-eyebrow">{{ t("detail.out") }}</div>
							<div
								class="data-value"
								:style="{ color: dialogCell.is_today && !dialogCell.out_time ? colors.ink4 : colors.red }"
							>{{ dialogCell.out_time || "—:—" }}</div>
						</div>
						<div class="data-cell span-2">
							<div class="dlg-eyebrow">{{ t("detail.dur") }}</div>
							<div class="data-value">{{ dialogCell.hours ? `${dialogCell.hours}h` : "—" }}</div>
						</div>
					</div>

					<div class="dlg-shift" v-if="dialogCell.shift_label && dialogCell.state !== 'holiday' && dialogCell.state !== 'rest'">
						<div class="dlg-shift-head">
							<span class="dlg-shift-eyebrow">▣ {{ t("detail.shift") }}</span>
							<span class="dlg-shift-label">{{ dialogCell.shift_label }}</span>
						</div>
						<div v-if="dialogCell.shift_start && dialogCell.shift_end" class="dlg-shift-time">
							{{ dialogCell.shift_start }}<span class="sep">—</span>{{ dialogCell.shift_end }}
						</div>
					</div>

					<button class="dlg-correction-btn" @click="openCorrectionRequest(dialogCell)">
						{{ t("detail.correction") }}
					</button>
				</div>
			</div>
		</teleport>
	</div>
</template>

<script setup>
import { computed, h, inject, onBeforeUnmount, reactive, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource } from "frappe-ui"
import { useRouter } from "vue-router"

import {
	getCalendarGridStyle,
	getCalendarWeekCount,
	padCalendarDaysToFullWeeks,
} from "@/components/attendanceCalendarLayout"
import {
	ATTENDANCE_ANOMALY_COLOR,
	getAttendanceAnomalyLabel,
	getAttendanceAnomalyTitle,
	hasAttendanceAnomaly,
} from "@/utils/attendanceAnomaly"

const dayjs = inject("$dayjs")
const employee = inject("$employee")
const router = useRouter()

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)
const dialogDay = ref(null)
const selectedDay = ref(null)

const THEME_SURFACE = {
	light: { bg: "#f1eee7", surface: "#ffffff", surface2: "#faf8f2", ink: "#0a0a0a", ink2: "#3f3d38", ink3: "#787570", ink4: "#adaaa3", ink5: "#d8d5cd", hairline: "#e3dfd4", hairline2: "#ede9dd" },
	dark: { bg: "#121212", surface: "#1e1e1e", surface2: "#252525", ink: "#e8e8e8", ink2: "#c0bdb6", ink3: "#8a8884", ink4: "#5c5955", ink5: "#3a3835", hairline: "#333333", hairline2: "#2a2a2a" },
}

const colors = reactive({
	...THEME_SURFACE.light,
	green: "#16a34a",
	green_dk: "#15803d",
	green_lt: "#86efac",
	roster_border: "#bbf7d0",
	red: "#dc2626",
	amber_dk: "#b45309",
	blue: "#2563eb",
	blue_dk: "#1d4ed8",
	heat_05: "#bbf7d0",
	heat_075: "#86efac",
	heat_1: "#4ade80",
	heat_125: "#16a34a",
	heat_gte: "#166534",
	wfh: "#dbeafe",
	half: "#fef3c7",
	leave: "#fde68a",
	absent: "#fecaca",
	holiday: "#fee2e2",
	rest: "#fde68a",
	anomaly: ATTENDANCE_ANOMALY_COLOR,
	anomaly_bg: "#fee2e2",
})

function syncCalendarTheme() {
	const isDark = document.documentElement.getAttribute("data-theme") === "dark"
	Object.assign(colors, isDark ? THEME_SURFACE.dark : THEME_SURFACE.light)
}
syncCalendarTheme()

const themeObserver = typeof MutationObserver !== "undefined"
	? new MutationObserver(syncCalendarTheme)
	: null
themeObserver?.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] })

const messages = {
	zh: {
		prev: "上个月",
		next: "下个月",
		close: "关闭",
		weekdays: ["日", "一", "二", "三", "四", "五", "六"],
		legend: {
			work: "出勤",
			wfh: "居家",
			half: "半天",
			leave: "请假",
			absent: "缺勤",
			roster: "已排班",
			holiday: "节假日",
			rest: "休",
			today: "今日",
			anomaly: "异常",
		},
		badge: {
			work: "出勤",
			wfh: "居家",
			half: "半天",
			leave: "请假",
			absent: "缺勤",
			holiday: "节",
			rest: "休",
		},
		monthLabel: (y, m) => `${y}年${m}月`,
		meta: { hours: "h", days: "天", avg: "日均" },
		summary: { title: "月度汇总", totalHours: "本月工时", workDays: "出勤日", avgHours: "日均" },
		detail: {
			today: "今日",
			selected: "日详情",
			status: "考勤状态",
			in: "签到",
			out: "签退",
			dur: "工作时长",
			shift: "班次",
			holiday: "节假日",
			ongoing: "工作中",
			correction: "申请补卡",
		},
		tip: "点击日期查看详情",
	},
	ja: {
		prev: "前の月",
		next: "次の月",
		close: "閉じる",
		weekdays: ["日", "月", "火", "水", "木", "金", "土"],
		legend: {
			work: "出勤",
			wfh: "在宅",
			half: "半休",
			leave: "休暇",
			absent: "欠勤",
			roster: "シフト",
			holiday: "祝日",
			rest: "休",
			today: "本日",
			anomaly: "異常",
		},
		badge: {
			work: "出勤",
			wfh: "在宅",
			half: "半休",
			leave: "休暇",
			absent: "欠勤",
			holiday: "祝",
			rest: "休",
		},
		monthLabel: (y, m) => `${y}年${m}月`,
		meta: { hours: "h", days: "日", avg: "平均" },
		summary: { title: "月次サマリー", totalHours: "今月時間", workDays: "出勤日", avgHours: "平均" },
		detail: {
			today: "本日",
			selected: "日詳細",
			status: "勤怠ステータス",
			in: "出勤",
			out: "退勤",
			dur: "勤務時間",
			shift: "シフト",
			holiday: "祝日",
			ongoing: "勤務中",
			correction: "打刻修正申請",
		},
		tip: "日付をタップで詳細",
	},
	en: {
		prev: "Prev",
		next: "Next",
		close: "Close",
		weekdays: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
		legend: {
			work: "In",
			wfh: "WFH",
			half: "Half",
			leave: "Leave",
			absent: "Absent",
			roster: "Roster",
			holiday: "Holiday",
			rest: "Off",
			today: "Today",
			anomaly: "Issue",
		},
		badge: {
			work: "IN",
			wfh: "WFH",
			half: "½",
			leave: "LV",
			absent: "ABS",
			holiday: "HOL",
			rest: "OFF",
		},
		monthLabel: (y, m) =>
			`${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][m - 1]} ${y}`,
		meta: { hours: "h", days: "d", avg: "Avg" },
		summary: { title: "Month Summary", totalHours: "Month Hours", workDays: "Days", avgHours: "Avg" },
		detail: {
			today: "Today",
			selected: "Detail",
			status: "Status",
			in: "In",
			out: "Out",
			dur: "Worked",
			shift: "Shift",
			holiday: "Holiday",
			ongoing: "Working",
			correction: "Correction request",
		},
		tip: "Tap a day for details",
	},
}

function getLang() {
	return window.frappe?.boot?.lang || "zh"
}

function t(path) {
	const dict = messages[getLang()] || messages.zh
	const segs = path.split(".")
	let cur = dict
	for (const s of segs) cur = cur?.[s]
	return cur != null ? cur : path
}

const weekdayHeaders = computed(() => (messages[getLang()] || messages.zh).weekdays)

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

const rosterMap = computed(() => {
	const map = {}
	for (const entry of rosterCalendarResource.data?.entries || []) {
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

const todayStr = dayjs().format("YYYY-MM-DD")

const metaLabels = computed(() => {
	const M = messages[getLang()] || messages.zh
	return M.meta
})

const monthTitle = computed(() => {
	const M = messages[getLang()] || messages.zh
	return M.monthLabel(currentYear.value, currentMonth.value)
})

const monthCells = computed(() => {
	const year = currentYear.value
	const month = currentMonth.value
	const lastDay = new Date(year, month, 0).getDate()
	const cells = []
	for (let d = 1; d <= lastDay; d++) {
		const dateObj = new Date(year, month - 1, d)
		const weekday = dateObj.getDay()
		const dateStr = `${year}-${String(month).padStart(2, "0")}-${String(d).padStart(2, "0")}`
		const rawAttendance = attendanceMap.value[dateStr] || null
		const attendanceEntry =
			typeof rawAttendance === "string"
				? { attendance: rawAttendance }
				: rawAttendance || {}
		const roster = rosterMap.value[dateStr] || null
		const holiday = holidayMap.value[dateStr] || null
		const anomaly = attendanceEntry.anomaly || null

		const state = deriveState(attendanceEntry, roster, holiday)
		const hours = toNumber(attendanceEntry.working_hours)
		cells.push({
			day: d,
			dateStr,
			weekday,
			state,
			hours,
			in_time: formatTime(attendanceEntry.in_time),
			out_time: formatTime(attendanceEntry.out_time),
			shift_label: roster?.shift_label || "",
			shift_start: extractTime(roster?.custom_start_time || roster?.scheduled_time?.split?.("-")?.[0]),
			shift_end: extractTime(roster?.custom_end_time || roster?.scheduled_time?.split?.("-")?.[1]),
			scheduled_time: roster?.scheduled_time || "",
			holiday: holiday && !holiday.weekly_off ? holiday.description : "",
			is_today: dateStr === todayStr,
			anomaly,
			anomaly_label: getAttendanceAnomalyLabel(anomaly, getLang()),
		})
	}
	return cells
})

const calendarCells = computed(() => {
	const lead = new Date(currentYear.value, currentMonth.value - 1, 1).getDay()
	const blanks = Array.from({ length: lead }, (_, i) => ({ empty: true, key: `bl-${i}` }))
	const days = monthCells.value.map((c) => ({ ...c, key: `d-${c.day}` }))
	return padCalendarDaysToFullWeeks([...blanks, ...days]).map((c, i) =>
		c.key ? c : { ...c, key: `pad-${i}` },
	)
})

const weekCount = computed(() => getCalendarWeekCount(calendarCells.value))
const calendarGridStyle = computed(() => getCalendarGridStyle(weekCount.value))

const monthSummary = computed(() => {
	let workDays = 0
	let hours = 0
	for (const c of monthCells.value) {
		if (c.state === "work" || c.state === "wfh") {
			workDays += 1
			hours += c.hours || 0
		} else if (c.state === "half") {
			workDays += 0.5
			hours += c.hours || 0
		}
	}
	const avg = workDays ? Math.round((hours / workDays) * 10) / 10 : 0
	return {
		workDays: trim(workDays),
		hours: trim(Math.round(hours * 10) / 10),
		avg,
	}
})

const dialogCell = computed(() => {
	if (dialogDay.value == null) return null
	return monthCells.value.find((c) => c.day === dialogDay.value) || null
})

const legendItems = computed(() => {
	return [
		{ key: "work", style: { background: colors.heat_125 } },
		{ key: "anomaly", style: { background: colors.anomaly_bg, border: `1.5px solid rgba(220,38,38,0.45)` } },
		// 数据齐了再放开 ↓
		// { key: "wfh", style: { background: colors.wfh } },
		// { key: "half", style: { background: colors.half } },
		// { key: "leave", style: { background: colors.leave } },
		// { key: "absent", style: { background: colors.absent } },
		{ key: "today", style: { background: "#fff", boxShadow: `0 0 0 1.5px ${colors.green}, 0 0 4px rgba(22,163,74,0.4)` } },
		{ key: "rest", style: { background: colors.rest } },
		{ key: "holiday", style: { background: colors.holiday } },
		{ key: "roster", style: { background: "#fff", border: `1.5px solid ${colors.roster_border}` } },
	]
})

function deriveState(attendanceEntry, roster, holiday) {
	if (hasAttendanceAnomaly(attendanceEntry?.anomaly)) return "anomaly"
	const status = attendanceEntry?.attendance
	if (status) {
		const m = {
			Present: "work",
			"Work From Home": "wfh",
			"Half Day": "half",
			"On Leave": "leave",
			// 暂时按"休"展示，等业务区分缺勤/休时再恢复 ↓
			Absent: "rest",
			// Absent: "absent",
			Holiday: "holiday",
		}
		if (m[status]) return m[status]
	}
	if (holiday && !holiday.weekly_off) return "holiday"
	if (roster) return "roster"
	if (holiday?.weekly_off) return "rest"
	return "empty"
}

function toNumber(v) {
	const n = Number(v)
	return Number.isFinite(n) ? Math.round(n * 10) / 10 : 0
}

function trim(n) {
	if (Number.isInteger(n)) return n
	return Math.round(n * 10) / 10
}

function formatTime(v) {
	if (!v) return ""
	const s = String(v)
	const m = s.match(/(\d{1,2}):(\d{2})/)
	if (m) return `${m[1].padStart(2, "0")}:${m[2]}`
	return s
}

function extractTime(v) {
	if (!v) return ""
	const s = String(v).trim()
	const m = s.match(/(\d{1,2}):(\d{2})/)
	if (m) return `${m[1].padStart(2, "0")}:${m[2]}`
	return s
}

function isDarkHeatCell(c) {
	return c.state === "work" && (c.hours || 0) / 8 >= 1.25
}

function isWorkLike(c) {
	return c.state === "work" || c.state === "wfh" || c.state === "half"
}

function isAttendanceDetailVisible(c) {
	return isWorkLike(c) || c.state === "anomaly"
}

function cellBackground(c) {
	if (c.state === "anomaly") return colors.anomaly_bg
	switch (c.state) {
		case "work": {
			const r = (c.hours || 0) / 8
			if (r < 0.5) return colors.heat_05
			if (r < 0.75) return colors.heat_075
			if (r < 1) return colors.heat_1
			if (r < 1.25) return colors.heat_125
			return colors.heat_gte
		}
		case "wfh":
			return colors.wfh
		case "half":
			return colors.half
		case "leave":
			return colors.leave
		case "absent":
			return colors.absent
		case "holiday":
			return colors.holiday
		case "rest":
			return colors.rest
		case "roster":
			return "#ffffff"
		default:
			return "#ffffff"
	}
}

function cellStyleFor(c) {
	const bg = cellBackground(c)
	let border = "1px solid transparent"
	let boxShadow = "none"

	if (c.state === "roster") border = `1.5px solid ${colors.roster_border}`
	else if (c.state === "anomaly") border = `1.5px solid rgba(220,38,38,0.45)`
	else if (c.state === "empty") border = `1px solid ${colors.hairline2}`
	else if (c.state === "rest") border = `1px solid ${colors.hairline2}`
	else if (c.state === "holiday") border = `1px solid rgba(220,38,38,0.18)`

	const isSelected = selectedDay.value === c.day
	const isToday = c.is_today
	if (isSelected) {
		boxShadow = `0 0 0 2px ${colors.green}, 0 0 12px rgba(22,163,74,0.35)`
	} else if (isToday) {
		boxShadow = `0 0 0 2px ${colors.ink}, 0 0 0 4px ${colors.surface}`
	}

	return {
		background: bg,
		border,
		boxShadow,
		zIndex: isSelected || isToday ? 2 : 1,
	}
}

function cellClasses(c) {
	return [`state-${c.state}`, c.is_today ? "is-today" : "", selectedDay.value === c.day ? "is-selected" : ""]
}

function dateColor(c) {
	if (c.state === "anomaly") return colors.anomaly
	if (isDarkHeatCell(c)) return "#ffffff"
	if (showWeekendTint(c)) {
		return c.weekday === 0 ? colors.red : colors.blue
	}
	return colors.ink
}

function showWeekendTint(c) {
	return (c.weekday === 0 || c.weekday === 6) && (c.state === "empty" || c.state === "rest")
}

function showWeekendDot(c) {
	if (!(c.weekday === 0 || c.weekday === 6)) return false
	return c.state !== "work" && c.state !== "wfh" && c.state !== "half"
}

function cellBadge(c) {
	const M = messages[getLang()] || messages.zh
	if (c.state === "anomaly") return getAttendanceAnomalyTitle(getLang())
	if (c.state === "roster") return c.shift_label || M.legend.roster
	return M.badge[c.state] || ""
}

function badgeStyle(c) {
	if (c.state === "anomaly") {
		return { color: colors.anomaly, background: "rgba(220,38,38,0.14)" }
	}
	const dark = isDarkHeatCell(c)
	const color = dark
		? "#ffffff"
		: {
				work: colors.green_dk,
				wfh: colors.blue_dk,
				half: colors.amber_dk,
				leave: colors.amber_dk,
				absent: colors.red,
				holiday: colors.red,
				rest: colors.ink3,
				roster: colors.green_dk,
		  }[c.state] || colors.ink3
	const bg = dark
		? "rgba(255,255,255,0.18)"
		: {
				work: "rgba(22,163,74,0.14)",
				wfh: "rgba(37,99,235,0.14)",
				half: "rgba(180,83,9,0.14)",
				leave: "rgba(180,83,9,0.14)",
				absent: "rgba(220,38,38,0.14)",
				holiday: "rgba(220,38,38,0.14)",
				rest: "transparent",
				roster: "rgba(22,163,74,0.10)",
		  }[c.state] || "transparent"
	return { color, background: bg }
}

function statusColor(c) {
	return {
		anomaly: colors.anomaly,
		work: colors.green_dk,
		wfh: colors.blue_dk,
		half: colors.amber_dk,
		leave: colors.amber_dk,
		absent: colors.red,
		holiday: colors.red,
		rest: colors.ink3,
		roster: colors.green_dk,
		empty: colors.ink3,
	}[c.state] || colors.ink3
}

function statusLabel(c) {
	const M = messages[getLang()] || messages.zh
	return M.legend[c.state] || "—"
}

function detailPillStyle(c) {
	const bg = c.state === "roster" ? "#ffffff" : cellBackground(c)
	const border = c.state === "roster" ? `1.5px solid ${colors.roster_border}` : `1px solid ${colors.hairline2}`
	return { background: bg, border }
}

const StateIcon = {
	props: ["cell"],
	setup(props) {
		return () => {
			const s = props.cell.state
			const stroke =
				s === "anomaly"
					? colors.anomaly
					: s === "work"
					? colors.green_dk
					: s === "wfh"
					? colors.blue_dk
					: s === "half" || s === "leave"
					? colors.amber_dk
					: s === "absent"
					? colors.red
					: s === "holiday"
					? colors.red
					: s === "roster"
					? colors.green_dk
					: colors.ink3
			const svg = (children, attrs = {}) =>
				h(
					"svg",
					Object.assign(
						{
							width: 20,
							height: 20,
							viewBox: "0 0 24 24",
							fill: "none",
							stroke,
							"stroke-width": "1.8",
							"stroke-linecap": "round",
							"stroke-linejoin": "round",
						},
						attrs,
					),
					children,
				)
			switch (s) {
				case "work":
					return svg([h("path", { d: "M5 12l4 4L19 7" })], { "stroke-width": "2.2" })
				case "wfh":
					return svg([h("path", { d: "M3 11L12 4l9 7M5 10v10h14V10" })])
				case "half":
					return svg([
						h("circle", { cx: 12, cy: 12, r: 9 }),
						h("path", { d: "M12 3a9 9 0 0 1 0 18", fill: stroke, stroke: "none" }),
					])
				case "leave":
					return svg([h("path", { d: "M4 4v16M4 4l10 3v8L4 12" })])
				case "absent":
					return svg([h("path", { d: "M6 6l12 12M18 6L6 18" })], { "stroke-width": "2.2" })
				case "anomaly":
					return svg([
						h("path", { d: "M12 9v4" }),
						h("path", { d: "M12 17h.01" }),
						h("path", {
							d: "M10.3 3.9 2.5 18a2 2 0 0 0 1.7 3h15.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z",
						}),
					])
				case "holiday":
					return h(
						"svg",
						{ width: 18, height: 18, viewBox: "0 0 24 24", fill: stroke, stroke: "none" },
						[h("path", { d: "M12 2l2.4 6.8H21l-5.4 4 2 6.8L12 15.6 6.4 19.6l2-6.8L3 8.8h6.6z" })],
					)
				case "roster":
					return svg([
						h("rect", { x: 3, y: 5, width: 18, height: 16, rx: 2 }),
						h("path", { d: "M3 9h18M8 3v4M16 3v4" }),
					])
				case "rest":
					return svg([h("path", { d: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" })])
				default:
					return svg([h("circle", { cx: 12, cy: 12, r: 9 })])
			}
		}
	},
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

function openDay(cell) {
	if (!cell?.day) return
	selectedDay.value = cell.day
	dialogDay.value = cell.day
}

function openCorrectionRequest(cell) {
	if (!cell?.dateStr) return
	closeDialog()
	router.push({
		name: "AttendanceCorrectionFormView",
		query: { date: cell.dateStr },
	})
}

function closeDialog() {
	dialogDay.value = null
}

function prevMonth() {
	if (currentMonth.value === 1) {
		currentMonth.value = 12
		currentYear.value -= 1
	} else {
		currentMonth.value -= 1
	}
}

function nextMonth() {
	if (currentMonth.value === 12) {
		currentMonth.value = 1
		currentYear.value += 1
	} else {
		currentMonth.value += 1
	}
}

watch([currentYear, currentMonth, () => employee?.data?.name], loadData, { immediate: true })

watch(monthCells, (cells) => {
	const today = cells.find((c) => c.is_today)
	if (today && selectedDay.value == null) {
		selectedDay.value = today.day
	} else if (selectedDay.value != null && !cells.find((c) => c.day === selectedDay.value)) {
		selectedDay.value = null
	}
})

onIonViewWillEnter(() => {
	loadData()
})

onBeforeUnmount(() => {
	themeObserver?.disconnect()
})
</script>

<style scoped>
.attn-root {
	display: flex;
	flex-direction: column;
	min-height: 0;
	flex: 1;
	gap: 8px;
	font-family: "Inter", -apple-system, system-ui, "PingFang SC", "Hiragino Sans", sans-serif;
	color: #0a0a0a;
}

.attn-skeleton {
	flex: 1;
	min-height: 240px;
	border-radius: 14px;
	background: #ede9dd;
	animation: attn-pulse 1.4s ease-in-out infinite;
}

@keyframes attn-pulse {
	0%, 100% { opacity: 1; }
	50% { opacity: 0.55; }
}

/* Month bar */
.month-bar {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 2px 0 4px;
}
.nav-btn {
	width: 34px;
	height: 34px;
	border-radius: 999px;
	background: #ffffff;
	border: 1px solid #e3dfd4;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
	color: #0a0a0a;
	box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}
.month-label-wrap {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 4px;
}
.month-label {
	font-size: 18px;
	font-weight: 700;
	letter-spacing: -0.02em;
	color: #0a0a0a;
	font-variant-numeric: tabular-nums;
}

/* Legend */
.legend {
	background: #ffffff;
	border: 1px solid #e3dfd4;
	border-radius: 12px;
	padding: 8px 12px;
	display: grid;
	grid-template-columns: repeat(5, 1fr);
	column-gap: 6px;
	row-gap: 6px;
	box-shadow: 0 1px 2px rgba(20, 18, 12, 0.03);
}
.legend-chip {
	display: flex;
	align-items: center;
	gap: 5px;
	font-size: 10px;
	color: #3f3d38;
	font-weight: 500;
	white-space: nowrap;
	min-width: 0;
}
.swatch {
	flex-shrink: 0;
	width: 11px;
	height: 11px;
	border-radius: 3px;
	border: 1px solid rgba(0, 0, 0, 0.05);
}
.legend-text {
	overflow: hidden;
	text-overflow: ellipsis;
}

/* Week header */
.week-header {
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	column-gap: 4px;
	padding: 2px 0;
}
.weekday {
	text-align: center;
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.1em;
	color: #787570;
}
.wd-sun { color: #dc2626; }
.wd-sat { color: #2563eb; }

/* Calendar */
.calendar-grid {
	flex: 1;
	min-height: 0;
	display: grid;
	grid-template-columns: repeat(7, 1fr);
	column-gap: 4px;
	row-gap: 4px;
}
.cell-blank {
	border-radius: 9px;
}
.cell {
	position: relative;
	min-width: 0;
	min-height: 0;
	overflow: hidden;
	border-radius: 9px;
	padding: 5px 6px 4px;
	cursor: pointer;
	display: flex;
	flex-direction: column;
	justify-content: space-between;
	text-align: left;
	transition: transform 100ms ease;
	font-family: inherit;
}
.cell:active {
	transform: scale(0.97);
}
.cell.state-anomaly {
	color: #7f1d1d;
}
.cell-top {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	line-height: 1;
}
.cell-date {
	font-variant-numeric: tabular-nums;
	font-size: 14px;
	font-weight: 700;
	letter-spacing: -0.02em;
}
.weekend-dot {
	width: 3px;
	height: 3px;
	border-radius: 999px;
	opacity: 0.5;
	margin-top: 4px;
	margin-right: 1px;
	display: inline-block;
}
.cell-bottom {
	display: flex;
	align-items: center;
	min-height: 14px;
}
.cell-badge {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	font-weight: 700;
	letter-spacing: 0.04em;
	padding: 1.5px 4px;
	border-radius: 4px;
	white-space: nowrap;
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
}

/* Detail strip */
.detail-strip {
	margin-top: 8px;
	background: #ffffff;
	border: 1px solid #e3dfd4;
	border-radius: 14px;
	padding: 12px 14px;
	display: flex;
	align-items: center;
	gap: 12px;
	min-height: 72px;
	box-shadow: 0 1px 2px rgba(20, 18, 12, 0.03), 0 4px 16px -10px rgba(20, 18, 12, 0.06);
}
.month-summary-strip {
	justify-content: space-between;
}
.month-summary-head {
	display: flex;
	flex-direction: column;
	gap: 4px;
	min-width: 0;
}
.month-summary-kicker {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	font-weight: 700;
	letter-spacing: 0.14em;
	color: #adaaa3;
	white-space: nowrap;
}
.month-summary-head strong {
	font-size: 17px;
	line-height: 1.15;
	font-weight: 800;
	color: #0a0a0a;
	letter-spacing: 0;
}
.month-summary-metrics {
	display: grid;
	grid-template-columns: repeat(3, minmax(52px, 1fr));
	gap: 12px;
	margin-left: auto;
}
.month-summary-metric {
	display: flex;
	flex-direction: column;
	align-items: flex-end;
	gap: 4px;
	min-width: 0;
}
.month-summary-metric span {
	font-size: 10px;
	font-weight: 700;
	color: #787570;
	white-space: nowrap;
}
.month-summary-metric strong {
	font-size: 22px;
	line-height: 1;
	font-weight: 800;
	color: #0a0a0a;
	letter-spacing: 0;
	font-variant-numeric: tabular-nums;
	white-space: nowrap;
}
.month-summary-metric small {
	margin-left: 2px;
	font-size: 11px;
	font-weight: 700;
	color: #787570;
}

/* Dialog */
.dlg-mask {
	position: fixed;
	inset: 0;
	background: rgba(20, 18, 12, 0.42);
	backdrop-filter: blur(2px);
	z-index: 1000;
	display: flex;
	align-items: center;
	justify-content: center;
	animation: dlg-fade 180ms ease-out;
	padding: 20px;
}
.dlg-card {
	width: 100%;
	max-width: 360px;
	background: #ffffff;
	border-radius: 18px;
	padding: 18px;
	box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.4), 0 1px 2px rgba(0, 0, 0, 0.1);
	animation: dlg-pop 220ms cubic-bezier(0.22, 1.4, 0.36, 1);
}
@keyframes dlg-fade {
	from { opacity: 0; }
	to { opacity: 1; }
}
@keyframes dlg-pop {
	from { opacity: 0; transform: scale(0.96) translateY(8px); }
	to { opacity: 1; transform: scale(1) translateY(0); }
}
.dlg-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 12px;
}
.dlg-eyebrow {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	color: #adaaa3;
	letter-spacing: 0.14em;
	font-weight: 700;
}
.dlg-title {
	margin-top: 4px;
	font-size: 26px;
	font-weight: 700;
	letter-spacing: -0.03em;
	color: #0a0a0a;
	font-variant-numeric: tabular-nums;
	display: flex;
	align-items: baseline;
	gap: 8px;
}
.dlg-weekday {
	font-size: 12px;
	font-weight: 700;
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	letter-spacing: 0.1em;
}
.dlg-holiday-name {
	margin-top: 6px;
	font-size: 13px;
	color: #dc2626;
	font-weight: 600;
}
.dlg-close {
	width: 32px;
	height: 32px;
	border-radius: 999px;
	background: #faf8f2;
	border: 1px solid #e3dfd4;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
	color: #3f3d38;
	flex-shrink: 0;
}
.dlg-status {
	margin-top: 14px;
	padding: 12px 14px;
	background: #faf8f2;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}
.dlg-status-label {
	margin-top: 6px;
	font-size: 18px;
	font-weight: 700;
	letter-spacing: -0.01em;
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}
.ongoing-chip {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 10px;
	padding: 2px 7px;
	background: rgba(22, 163, 74, 0.12);
	color: #15803d;
	border-radius: 999px;
	letter-spacing: 0.08em;
	font-weight: 700;
}
.dlg-anomaly-reason {
	display: block;
	margin-top: 4px;
	font-size: 12px;
	line-height: 1.35;
	font-weight: 800;
	color: #dc2626;
}
.dlg-status-icon {
	width: 48px;
	height: 48px;
	border-radius: 14px;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}
.dlg-grid {
	margin-top: 10px;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 8px;
}
.data-cell {
	padding: 10px 12px;
	background: #faf8f2;
	border-radius: 10px;
}
.data-cell.span-2 {
	grid-column: span 2;
}
.data-value {
	margin-top: 4px;
	font-size: 20px;
	font-weight: 700;
	color: #0a0a0a;
	font-variant-numeric: tabular-nums;
	letter-spacing: -0.02em;
}
.dlg-shift {
	margin-top: 10px;
	padding: 12px 14px;
	background: rgba(22, 163, 74, 0.05);
	border: 1px solid rgba(22, 163, 74, 0.18);
	border-radius: 12px;
}
.dlg-shift-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
}
.dlg-shift-eyebrow {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	color: #15803d;
	letter-spacing: 0.14em;
	font-weight: 700;
}
.dlg-shift-label {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	color: #787570;
	letter-spacing: 0.1em;
	font-weight: 500;
}
.dlg-shift-time {
	margin-top: 6px;
	font-size: 22px;
	font-weight: 700;
	color: #0a0a0a;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
}
.dlg-shift-time .sep {
	color: #adaaa3;
	margin: 0 4px;
	font-weight: 400;
}
.dlg-correction-btn {
	width: 100%;
	min-height: 42px;
	margin-top: 10px;
	border: 1px solid #d8d5cd;
	border-radius: 8px;
	background: #ffffff;
	color: #1f2937;
	font-size: 14px;
	font-weight: 700;
}
</style>
