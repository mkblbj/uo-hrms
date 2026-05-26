export function buildAttendanceCorrectionTabs(hasApprovals, pendingCount = 0) {
	const tabs = [{ key: "mine", label: "补卡申请" }]
	if (hasApprovals) {
		tabs.push({
			key: "approvals",
			label: pendingCount ? `待我审批 ${pendingCount}` : "待我审批",
		})
	}
	return tabs
}

export function getCorrectionStatusTheme(status) {
	const themes = {
		Draft: "gray",
		Pending: "orange",
		Rejected: "red",
		Applied: "green",
		"Apply Failed": "red",
	}
	return themes[status] || "gray"
}

export function formatCorrectionDateTime(value) {
	if (!value) return ""
	return String(value).replace("T", " ").slice(0, 16)
}

export function buildCorrectionPayload(form) {
	return {
		attendance_date: form.attendance_date,
		request_type: form.request_type,
		requested_log_type: form.requested_log_type,
		requested_time: form.requested_time,
		original_checkin: form.original_checkin || null,
		reason: String(form.reason || "").trim(),
	}
}
