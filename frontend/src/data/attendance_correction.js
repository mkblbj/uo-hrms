import { createResource } from "frappe-ui"

const transformCorrectionRequests = (data) =>
	data.map((request) => {
		request.doctype = "Attendance Correction Request"
		return request
	})

export const attendanceCorrectionApprovalCount = createResource({
	url: "hrms.api.attendance_correction.get_attendance_correction_approval_count",
	auto: true,
	cache: "hrms:attendance_correction_approval_count",
})

export const myAttendanceCorrectionRequests = createResource({
	url: "hrms.api.attendance_correction.get_my_attendance_correction_requests",
	auto: true,
	cache: "hrms:my_attendance_correction_requests",
	transform(data) {
		return transformCorrectionRequests(data)
	},
})

export const pendingAttendanceCorrectionApprovals = createResource({
	url: "hrms.api.attendance_correction.get_pending_attendance_correction_approvals",
	auto: true,
	cache: "hrms:pending_attendance_correction_approvals",
	transform(data) {
		return transformCorrectionRequests(data)
	},
})
