import { reactive } from "vue"

export function useAttendanceDayDetails(fetchDetails) {
	const state = reactive({ date: null, data: null, loading: false, error: null })
	let requestId = 0
	return {
		state,
		async load(date, employee) {
			const currentRequest = ++requestId
			Object.assign(state, { date, data: null, loading: true, error: null })
			try {
				const data = await fetchDetails({ date, employee })
				if (currentRequest === requestId) state.data = data
			} catch (error) {
				if (currentRequest === requestId) state.error = error
			} finally {
				if (currentRequest === requestId) state.loading = false
			}
		},
		reset() {
			requestId++
			Object.assign(state, { date: null, data: null, loading: false, error: null })
		},
	}
}

export function formatDetailHours(value) {
	if (value == null || value === "" || !Number.isFinite(Number(value))) return "—"
	return String(Math.round(Number(value) * 100) / 100)
}

export function formatDetailTime(value, day, seconds = false) {
	if (!value) return "—"
	const match = String(value).match(/(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(:\d{2})?/)
	if (!match) return String(value)
	const time = match[2] + (seconds ? match[3] || ":00" : "")
	if (match[1] === day) return time
	const [, month, date] = match[1].split("-")
	return `${Number(month)}/${Number(date)} ${time}`
}
