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
				<span class="month-meta">{{ monthMeta }}</span>
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

		<!-- Detail Strip -->
		<div class="detail-strip" v-if="selectedCell">
			<div class="ds-left">
				<span class="ds-label">{{ selectedCell.is_today ? t("detail.today") : t("detail.selected") }}</span>
				<span class="ds-date">{{ currentMonth }}/{{ selectedCell.day }}</span>
				<span
					class="ds-weekday"
					:style="{ color: selectedCell.weekday === 0 ? colors.red : selectedCell.weekday === 6 ? colors.blue : colors.ink3 }"
				>{{ weekdayHeaders[selectedCell.weekday] }}</span>
			</div>
			<div class="ds-main">
				<component :is="DetailMain" :cell="selectedCell" />
				<component :is="DetailSub" :cell="selectedCell" />
			</div>
			<div class="ds-right" :style="detailPillStyle(selectedCell)">
				<span
					v-if="selectedCell.is_today && !selectedCell.out_time && isWorkLike(selectedCell)"
					class="ongoing-dot"
				/>
				<component :is="StateIcon" :cell="selectedCell" />
			</div>
		</div>
		<div class="detail-strip detail-empty" v-else>
			<span class="empty-dot" />
			<span class="empty-tip">{{ t("tip") }}</span>
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
							</div>
						</div>
						<div class="dlg-status-icon" :style="detailPillStyle(dialogCell)">
							<component :is="StateIcon" :cell="dialogCell" />
						</div>
					</div>

					<div class="dlg-grid" v-if="isWorkLike(dialogCell)">
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
				</div>
			</div>
		</teleport>
	</div>
</template>

<script setup>
import { computed, h, inject, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { createResource } from "frappe-ui"

import {
	getCalendarGridStyle,
	getCalendarWeekCount,
	padCalendarDaysToFullWeeks,
} from "@/components/attendanceCalendarLayout"

const dayjs = inject("$dayjs")
const employee = inject("$employee")

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)
const dialogDay = ref(null)
const selectedDay = ref(null)

const colors = {
	bg: "#f1eee7",
	surface: "#ffffff",
	surface2: "#faf8f2",
	ink: "#0a0a0a",
	ink2: "#3f3d38",
	ink3: "#787570",
	ink4: "#adaaa3",
	ink5: "#d8d5cd",
	hairline: "#e3dfd4",
	hairline2: "#ede9dd",
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
}

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
		meta: { hours: "h", days: "d", avg: "AVG" },
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
		meta: { hours: "h", days: "d", avg: "AVG" },
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
		meta: { hours: "h", days: "d", avg: "AVG" },
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

const monthMeta = computed(() => {
	const lang = getLang()
	const M = messages[lang] || messages.zh
	const s = monthSummary.value
	return `${s.hours}${M.meta.hours} · ${s.workDays}${M.meta.days} · ${M.meta.avg} ${s.avg}${M.meta.hours}`
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

const selectedCell = computed(() => {
	if (selectedDay.value == null) return null
	return monthCells.value.find((c) => c.day === selectedDay.value) || null
})

const dialogCell = computed(() => {
	if (dialogDay.value == null) return null
	return monthCells.value.find((c) => c.day === dialogDay.value) || null
})

const legendItems = computed(() => {
	return [
		{ key: "work", style: { background: colors.heat_125 } },
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

function cellBackground(c) {
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
	if (c.state === "roster") return c.shift_label || M.legend.roster
	return M.badge[c.state] || ""
}

function badgeStyle(c) {
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

const DetailMain = {
	props: ["cell"],
	setup(props) {
		return () => {
			const c = props.cell
			const isOngoing = c.is_today && !c.out_time && isWorkLike(c)
			if (c.state === "holiday") {
				return h(
					"span",
					{ class: "ds-main-line ds-main-text", style: { color: colors.ink } },
					c.holiday || statusLabel(c),
				)
			}
			if (isWorkLike(c)) {
				return h("span", { class: "ds-main-line ds-time" }, [
					c.in_time || "—:—",
					h("span", { class: "sep" }, "—"),
					isOngoing
						? h("span", { class: "ongoing-dots", style: { color: colors.green_dk } }, "·····")
						: c.out_time || "—:—",
				])
			}
			return h(
				"span",
				{ class: "ds-main-line ds-main-text", style: { color: statusColor(c) } },
				statusLabel(c),
			)
		}
	},
}

const DetailSub = {
	props: ["cell"],
	setup(props) {
		return () => {
			const c = props.cell
			const M = messages[getLang()] || messages.zh
			if (isWorkLike(c)) {
				const isOngoing = c.is_today && !c.out_time
				const parts = []
				parts.push(h("span", { class: "ds-mono" }, `${c.hours || 0}h`))
				if (c.shift_label) {
					parts.push(h("span", { class: "ds-bullet" }))
					parts.push(h("span", {}, `${M.detail.shift} ${c.shift_label}`))
				}
				if (isOngoing) {
					parts.push(h("span", { class: "ds-bullet" }))
					parts.push(
						h("span", { style: { color: colors.green_dk, fontWeight: 700 } }, `· ${M.detail.ongoing}`),
					)
				}
				return h("div", { class: "ds-sub" }, parts)
			}
			if (c.state === "roster") {
				const time =
					c.shift_start && c.shift_end ? `${c.shift_start}—${c.shift_end}` : c.scheduled_time || ""
				return h("div", { class: "ds-sub" }, [
					h("span", { class: "ds-mono" }, time),
					c.shift_label ? h("span", { class: "ds-bullet" }) : null,
					c.shift_label ? h("span", {}, `${M.detail.shift} ${c.shift_label}`) : null,
				])
			}
			if (c.state === "holiday") {
				return h("div", { class: "ds-sub-mono" }, M.detail.holiday)
			}
			return h("div", { class: "ds-sub-faint" }, c.state === "rest" ? M.legend.rest : "")
		}
	},
}

const StateIcon = {
	props: ["cell"],
	setup(props) {
		return () => {
			const s = props.cell.state
			const stroke =
				s === "work"
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
	gap: 2px;
}
.month-label {
	font-size: 18px;
	font-weight: 700;
	letter-spacing: -0.02em;
	color: #0a0a0a;
	font-variant-numeric: tabular-nums;
}
.month-meta {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	font-weight: 700;
	letter-spacing: 0.16em;
	color: #adaaa3;
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
.detail-empty {
	min-height: 48px;
	color: #787570;
	font-size: 12px;
}
.empty-dot {
	width: 6px;
	height: 6px;
	border-radius: 999px;
	background: #adaaa3;
}
.empty-tip {
	font-size: 12px;
}
.ds-left {
	display: flex;
	flex-direction: column;
	gap: 3px;
	min-width: 60px;
}
.ds-label {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	font-size: 9px;
	color: #adaaa3;
	letter-spacing: 0.16em;
	font-weight: 700;
}
.ds-date {
	font-size: 22px;
	font-weight: 700;
	color: #0a0a0a;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
	line-height: 1;
}
.ds-weekday {
	margin-top: 2px;
	font-size: 10px;
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	letter-spacing: 0.1em;
	font-weight: 600;
}
.ds-main {
	flex: 1;
	min-width: 0;
	display: flex;
	flex-direction: column;
	gap: 4px;
}
.ds-main-line {
	font-size: 18px;
	font-weight: 700;
	color: #0a0a0a;
	letter-spacing: -0.01em;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}
.ds-time {
	font-size: 22px;
	font-weight: 700;
	color: #0a0a0a;
	letter-spacing: -0.02em;
	font-variant-numeric: tabular-nums;
	line-height: 1.05;
}
.ds-time .sep {
	color: #adaaa3;
	font-weight: 400;
	margin: 0 4px;
}
.ongoing-dots {
	font-weight: 700;
}
.ds-sub {
	display: flex;
	align-items: baseline;
	gap: 8px;
	font-size: 11px;
	color: #787570;
	flex-wrap: wrap;
}
.ds-mono {
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	letter-spacing: 0.06em;
	font-variant-numeric: tabular-nums;
}
.ds-bullet {
	width: 2px;
	height: 2px;
	border-radius: 999px;
	background: #adaaa3;
	display: inline-block;
}
.ds-sub-mono {
	font-size: 11px;
	color: #787570;
	font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
	letter-spacing: 0.08em;
	font-weight: 700;
}
.ds-sub-faint {
	font-size: 11px;
	color: #adaaa3;
}
.ds-right {
	width: 44px;
	height: 44px;
	border-radius: 12px;
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;
	flex-shrink: 0;
}
.ongoing-dot {
	position: absolute;
	top: 4px;
	right: 4px;
	width: 7px;
	height: 7px;
	border-radius: 999px;
	background: #16a34a;
	box-shadow: 0 0 6px rgba(22, 163, 74, 0.7);
	animation: attn-pulse 1.6s ease-in-out infinite;
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
</style>
