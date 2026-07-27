const ROSTER_COPY = {
	pageTitle: {
		zh: "排班",
		ja: "シフト",
		en: "Shift",
	},
	viewSelector: {
		zh: "排班查看范围",
		ja: "シフト表示範囲",
		en: "Roster view",
	},
	myShift: {
		zh: "我的 Shift",
		ja: "私のシフト",
		en: "My Shift",
	},
	departmentShift: {
		zh: "部门 Shift",
		ja: "部門シフト",
		en: "Department Shift",
	},
	departmentSelector: {
		zh: "选择部门",
		ja: "部門を選択",
		en: "Select department",
	},
	submitPreference: {
		zh: "填写意愿",
		ja: "希望を入力",
		en: "Submit preference",
	},
	editPreference: {
		zh: "修改意愿",
		ja: "希望を変更",
		en: "Edit preference",
	},
	submitted: {
		zh: "已提交",
		ja: "提出済み",
		en: "Submitted",
	},
	scheduling: {
		zh: "正在编制排班",
		ja: "シフト編成中",
		en: "Scheduling in progress",
	},
	deadline: {
		zh: "截止 {date}",
		ja: "締切 {date}",
		en: "Due {date}",
	},
	previousMonth: {
		zh: "上个月",
		ja: "前の月",
		en: "Previous month",
	},
	nextMonth: {
		zh: "下个月",
		ja: "次の月",
		en: "Next month",
	},
	published: {
		zh: "已发布",
		ja: "公開済み",
		en: "Published",
	},
	periodMissing: {
		zh: "本月排班尚未发布",
		ja: "今月のシフトは未公開です",
		en: "This month's roster is not published",
	},
	departmentOffice: {
		zh: "办公室",
		ja: "事務",
		en: "Office",
	},
	departmentProduction: {
		zh: "生产",
		ja: "生産",
		en: "Production",
	},
	holiday: {
		zh: "节假日",
		ja: "祝日",
		en: "Holiday",
	},
	sale: {
		zh: "促销",
		ja: "セール",
		en: "Sale",
	},
	bigSale: {
		zh: "大型促销",
		ja: "大型セール",
		en: "Big sale",
	},
	saturday: {
		zh: "六",
		ja: "土",
		en: "Sat",
	},
	sunday: {
		zh: "日",
		ja: "日",
		en: "Sun",
	},
	actualShort: {
		zh: "实",
		ja: "実",
		en: "Act",
	},
	equivalentShort: {
		zh: "换",
		ja: "換",
		en: "Eq",
	},
	scheduledPeople: {
		zh: "实 {count}人",
		ja: "実 {count}人",
		en: "{count} scheduled",
	},
	equivalentPeople: {
		zh: "换算 {count}人",
		ja: "換算 {count}人",
		en: "{count} equivalent",
	},
	rest: {
		zh: "休",
		ja: "休",
		en: "Off",
	},
	emptyShort: {
		zh: "—",
		ja: "—",
		en: "—",
	},
	emptyDay: {
		zh: "当天没有计划排班",
		ja: "この日の予定シフトはありません",
		en: "No planned shift for this day",
	},
	customTime: {
		zh: "自定义班次",
		ja: "カスタムシフト",
		en: "Custom shift",
	},
	loading: {
		zh: "正在加载排班…",
		ja: "シフトを読み込み中…",
		en: "Loading roster…",
	},
	loadError: {
		zh: "排班加载失败",
		ja: "シフトを読み込めませんでした",
		en: "Could not load roster",
	},
	retry: {
		zh: "重试",
		ja: "再試行",
		en: "Retry",
	},
	noEmployee: {
		zh: "当前账号未关联员工资料",
		ja: "このアカウントに従業員情報がありません",
		en: "No employee record is linked to this account",
	},
	close: {
		zh: "关闭",
		ja: "閉じる",
		en: "Close",
	},
	shiftLabel: {
		zh: "班次",
		ja: "シフト",
		en: "Shift",
	},
	scheduledTime: {
		zh: "计划时间",
		ja: "予定時間",
		en: "Scheduled time",
	},
}

function dateKey(value) {
	if (!value) return ""
	if (typeof value === "string") return value.slice(0, 10)
	if (value instanceof Date && !Number.isNaN(value.getTime())) {
		const year = value.getFullYear()
		const month = String(value.getMonth() + 1).padStart(2, "0")
		const day = String(value.getDate()).padStart(2, "0")
		return `${year}-${month}-${day}`
	}
	return String(value).slice(0, 10)
}

function selectPrimaryEvent(events) {
	return [...events].sort((left, right) => {
		const priority = (event) => (["Major Sale", "Big Sale"].includes(event?.event_type) ? 2 : 1)
		return priority(right) - priority(left)
	})[0]
}

export function addRosterMonth({ year, month }, delta) {
	const index = Number(year) * 12 + Number(month) - 1 + Number(delta)
	return {
		year: Math.floor(index / 12),
		month: (((index % 12) + 12) % 12) + 1,
	}
}

export function resolveRosterInitialState({ now = new Date(), query = {} }) {
	return {
		scope: query.view === "department" ? "department" : "mine",
		year: now.getFullYear(),
		month: now.getMonth() + 1,
		legacyPeriod: typeof query.period === "string" ? query.period : "",
	}
}

export function getRosterCacheKey(scope, year, month, departmentCategory = "") {
	const monthKey = `${Number(year)}-${String(Number(month)).padStart(2, "0")}`
	if (scope === "department") {
		return `department:${departmentCategory || "default"}:${monthKey}`
	}
	return `${scope}:${monthKey}`
}

export function buildRosterCalendarCells({
	year,
	month,
	days = [],
	holidays = [],
	events = [],
	today = "",
}) {
	const dayByDate = new Map(days.map((day) => [dateKey(day.date), day]))
	const holidayByDate = new Map(
		holidays.map((holiday) => [dateKey(holiday.holiday_date), holiday])
	)
	const eventsByDate = new Map()
	for (const event of events) {
		const key = dateKey(event.event_date)
		const current = eventsByDate.get(key) || []
		current.push(event)
		eventsByDate.set(key, current)
	}

	const firstWeekday = new Date(year, month - 1, 1).getDay()
	const lastDay = new Date(year, month, 0).getDate()
	const required = firstWeekday + lastDay
	const cellCount = Math.max(35, Math.ceil(required / 7) * 7)
	const cells = Array.from({ length: firstWeekday }, () => ({
		empty: true,
		isPlaceholder: true,
		dateStr: "",
		data: null,
	}))

	for (let dayNumber = 1; dayNumber <= lastDay; dayNumber += 1) {
		const dateStr = `${Number(year)}-${String(Number(month)).padStart(2, "0")}-${String(
			dayNumber
		).padStart(2, "0")}`
		const weekday = new Date(year, month - 1, dayNumber).getDay()
		const holiday = holidayByDate.get(dateStr) || null
		const isWeeklyOff = Boolean(Number(holiday?.weekly_off || 0))
		cells.push({
			empty: false,
			isPlaceholder: false,
			dateStr,
			day: dayNumber,
			dayNumber,
			ariaLabel: dateStr,
			data: dayByDate.get(dateStr) || null,
			holiday,
			holidayName: holiday?.description || "",
			event: selectPrimaryEvent(eventsByDate.get(dateStr) || []) || null,
			isSunday: weekday === 0,
			isSaturday: weekday === 6,
			isToday: dateStr === dateKey(today),
			isHoliday: Boolean(holiday) && !isWeeklyOff,
			isWeeklyOff,
		})
	}

	while (cells.length < cellCount) {
		cells.push({
			empty: true,
			isPlaceholder: true,
			dateStr: "",
			data: null,
		})
	}
	return cells
}

export function resolveRosterFallbackMonth({ requested, response, initial }) {
	const fallback = response?.default_month
	if (!initial || response?.period || !fallback) return null
	if (
		Number(fallback.year) === Number(requested.year) &&
		Number(fallback.month) === Number(requested.month)
	) {
		return null
	}
	return {
		year: Number(fallback.year),
		month: Number(fallback.month),
	}
}

export function createRosterRequestGate() {
	let current = 0
	return {
		begin() {
			current += 1
			return current
		},
		isLatest(token) {
			return token === current
		},
	}
}

export function shouldCloseRosterSheet(deltaY) {
	return Number(deltaY) > 48
}

export function normalizeRosterLanguage(lang) {
	const normalized = String(lang || "")
		.toLowerCase()
		.split(/[-_]/)[0]
	return ["zh", "ja", "en"].includes(normalized) ? normalized : "zh"
}

export function getRosterCopy(key, lang, params = {}) {
	const language = normalizeRosterLanguage(lang)
	const template = ROSTER_COPY[key]?.[language] || ROSTER_COPY[key]?.zh
	if (!template) return key
	return template.replace(/\{(\w+)\}/g, (match, name) =>
		Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match
	)
}
