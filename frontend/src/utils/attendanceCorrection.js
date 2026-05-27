const COPY = {
	zh: {
		tabs: {
			mine: "补卡申请",
			approvals: "待我审批",
		},
		requestType: {
			"Forgot Check-in": "补上班卡",
			"Forgot Check-out": "补下班卡",
			"Correct Checkin Time": "修正打卡时间",
			Other: "其他",
		},
		status: {
			Draft: "草稿",
			Pending: "待审批",
			Rejected: "已拒绝",
			Applied: "已生效",
			"Apply Failed": "生效失败",
		},
		attendanceStatus: {
			Present: "出勤",
			"Work From Home": "居家办公",
			"Half Day": "半天",
			"On Leave": "请假",
			Absent: "缺勤",
			Holiday: "休息",
		},
		logType: {
			IN: "上班打卡",
			OUT: "下班打卡",
		},
		form: {
			newRequest: "新建补卡申请",
			submit: "提交",
			listTitle: "补卡申请",
			detailTitle: "补卡详情",
			empty: "暂无补卡申请",
			submitted: "补卡申请已提交",
			approved: "补卡申请已通过",
			rejected: "补卡申请已拒绝",
			completeRequired: "请填写所有必填项",
			selectOriginal: "请选择原始打卡",
			rejectionRequired: "请填写拒绝原因",
		},
		action: {
			approve: "通过",
			reject: "拒绝",
		},
		field: {
			attendanceDate: "考勤日",
			requestType: "申请类型",
			logType: "记录类型",
			requestedTime: "补卡时间",
			originalCheckin: "原始打卡",
			originalCheckinPlaceholder: "选择当天原始打卡",
			reason: "理由",
			reasonPlaceholder: "请填写补卡原因",
			rejectionReason: "拒绝原因",
			employee: "员工",
			status: "状态",
			resultAttendance: "结果考勤",
		},
		context: {
			title: "当天记录",
			shift: "班次",
			attendance: "考勤",
			checkins: "打卡记录",
			empty: "当天没有打卡记录",
		},
	},
	ja: {
		tabs: {
			mine: "打刻修正",
			approvals: "承認待ち",
		},
		requestType: {
			"Forgot Check-in": "出勤打刻の追加",
			"Forgot Check-out": "退勤打刻の追加",
			"Correct Checkin Time": "打刻時刻の修正",
			Other: "その他",
		},
		status: {
			Draft: "下書き",
			Pending: "承認待ち",
			Rejected: "却下",
			Applied: "反映済み",
			"Apply Failed": "反映失敗",
		},
		attendanceStatus: {
			Present: "出勤",
			"Work From Home": "在宅勤務",
			"Half Day": "半日",
			"On Leave": "休暇",
			Absent: "欠勤",
			Holiday: "休日",
		},
		logType: {
			IN: "出勤打刻",
			OUT: "退勤打刻",
		},
		form: {
			newRequest: "打刻修正申請",
			submit: "提出",
			listTitle: "打刻修正",
			detailTitle: "打刻修正詳細",
			empty: "打刻修正申請はありません",
			submitted: "打刻修正申請を提出しました",
			approved: "打刻修正申請を承認しました",
			rejected: "打刻修正申請を却下しました",
			completeRequired: "必須項目を入力してください",
			selectOriginal: "元の打刻を選択してください",
			rejectionRequired: "却下理由を入力してください",
		},
		action: {
			approve: "承認",
			reject: "却下",
		},
		field: {
			attendanceDate: "勤怠日",
			requestType: "申請タイプ",
			logType: "記録タイプ",
			requestedTime: "申請時刻",
			originalCheckin: "元の打刻",
			originalCheckinPlaceholder: "当日の元打刻を選択",
			reason: "理由",
			reasonPlaceholder: "修正理由を入力",
			rejectionReason: "却下理由",
			employee: "従業員",
			status: "ステータス",
			resultAttendance: "反映先勤怠",
		},
		context: {
			title: "当日の記録",
			shift: "シフト",
			attendance: "勤怠",
			checkins: "打刻",
			empty: "当日の打刻はありません",
		},
	},
	en: {
		tabs: {
			mine: "Correction Requests",
			approvals: "Pending Approvals",
		},
		requestType: {
			"Forgot Check-in": "Forgot Check-in",
			"Forgot Check-out": "Forgot Check-out",
			"Correct Checkin Time": "Correct Check-in Time",
			Other: "Other",
		},
		status: {
			Draft: "Draft",
			Pending: "Pending",
			Rejected: "Rejected",
			Applied: "Applied",
			"Apply Failed": "Apply Failed",
		},
		attendanceStatus: {
			Present: "Present",
			"Work From Home": "Work From Home",
			"Half Day": "Half Day",
			"On Leave": "On Leave",
			Absent: "Absent",
			Holiday: "Holiday",
		},
		logType: {
			IN: "Check-in",
			OUT: "Check-out",
		},
		form: {
			newRequest: "New Correction Request",
			submit: "Submit",
			listTitle: "Attendance Corrections",
			detailTitle: "Correction Request",
			empty: "No attendance correction requests found",
			submitted: "Attendance correction request submitted",
			approved: "Attendance correction request approved",
			rejected: "Attendance correction request rejected",
			completeRequired: "Please complete all required fields",
			selectOriginal: "Please select the original check-in",
			rejectionRequired: "Please enter a rejection reason",
		},
		action: {
			approve: "Approve",
			reject: "Reject",
		},
		field: {
			attendanceDate: "Attendance Date",
			requestType: "Request Type",
			logType: "Log Type",
			requestedTime: "Requested Time",
			originalCheckin: "Original Checkin",
			originalCheckinPlaceholder: "Select original check-in",
			reason: "Reason",
			reasonPlaceholder: "Enter reason",
			rejectionReason: "Rejection Reason",
			employee: "Employee",
			status: "Status",
			resultAttendance: "Result Attendance",
		},
		context: {
			title: "Day Context",
			shift: "Shift",
			attendance: "Attendance",
			checkins: "Check-ins",
			empty: "No check-ins for this day",
		},
	},
}

export function getCorrectionLang(lang) {
	const normalized = String(lang || globalThis.window?.frappe?.boot?.lang || "zh").split("-")[0]
	return COPY[normalized] ? normalized : "zh"
}

export function getAttendanceCorrectionCopy(key, lang) {
	const sectionEnd = key.indexOf(".")
	if (sectionEnd === -1) return key

	const section = key.slice(0, sectionEnd)
	const item = key.slice(sectionEnd + 1)
	const dict = COPY[getCorrectionLang(lang)] || COPY.zh
	return dict[section]?.[item] || COPY.zh[section]?.[item] || COPY.en[section]?.[item] || item
}

export function buildAttendanceCorrectionTabs(hasApprovals, pendingCount = 0, lang) {
	const tabs = [{ key: "mine", label: getAttendanceCorrectionCopy("tabs.mine", lang) }]
	if (hasApprovals) {
		const approvalLabel = getAttendanceCorrectionCopy("tabs.approvals", lang)
		tabs.push({
			key: "approvals",
			label: pendingCount ? `${approvalLabel} ${pendingCount}` : approvalLabel,
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

export function formatCorrectionDateTime(value, lang) {
	if (!value) return ""
	const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/)
	if (!match) return String(value).replace("T", " ").slice(0, 16)
	const [, year, month, day, hour, minute] = match
	if (getCorrectionLang(lang) === "en") return `${year}-${month}-${day} ${hour}:${minute}`
	return `${year}年${Number(month)}月${Number(day)}日 ${hour}:${minute}`
}

export function formatCorrectionClockTime(value) {
	const match = String(value || "").match(/[T ](\d{2}):(\d{2})/)
	return match ? `${match[1]}:${match[2]}` : ""
}

export function toNativeDateTimeInputValue(value) {
	if (!value) return ""
	const match = String(value).match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})/)
	return match ? `${match[1]}T${match[2]}:${match[3]}` : ""
}

export function fromNativeDateTimeInputValue(value) {
	if (!value) return ""
	const match = String(value).match(/^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/)
	return match ? `${match[1]} ${match[2]}:${match[3]}:00` : String(value)
}

export function buildOriginalCheckinOptions(checkins = [], lang) {
	return checkins.map((checkin) => ({
		label: `${formatCorrectionClockTime(checkin.time)} ${getAttendanceCorrectionCopy(
			`logType.${checkin.log_type || ""}`,
			lang
		)}`.trim(),
		value: checkin.name,
	}))
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
