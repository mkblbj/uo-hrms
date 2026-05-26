<template>
	<BaseLayout :pageTitle="__('Correction Request')" backRoute="/attendance-corrections">
		<template #body>
			<div v-if="doc.doc" class="correction-detail">
				<AttendanceCorrectionContextPanel :context="context.data" />
				<div class="detail-surface">
					<div v-for="row in rows" :key="row.label" class="detail-row">
						<span>{{ __(row.label) }}</span>
						<strong>{{ row.value || "-" }}</strong>
					</div>
				</div>

				<div v-if="canApprove" class="approval-actions">
					<FormField
						fieldtype="Small Text"
						fieldname="rejection_reason"
						v-model="rejectionReason"
						:label="__('Rejection Reason')"
					/>
					<ErrorMessage :message="approvalError || approveResource.error || rejectResource.error" />
					<div class="grid grid-cols-2 gap-3">
						<Button variant="subtle" theme="red" class="py-5" :loading="rejectResource.loading" @click="reject">
							{{ __("Reject") }}
						</Button>
						<Button variant="solid" theme="green" class="py-5" :loading="approveResource.loading" @click="approve">
							{{ __("Approve") }}
						</Button>
					</div>
				</div>
			</div>
			<div v-else class="flex flex-1 items-center justify-center bg-[#f1eee7] p-6">
				<LoadingIndicator class="h-6 w-6 text-gray-800" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { Button, ErrorMessage, LoadingIndicator, createDocumentResource, createResource, toast } from "frappe-ui"

import AttendanceCorrectionContextPanel from "@/components/AttendanceCorrectionContextPanel.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import FormField from "@/components/FormField.vue"
import { formatCorrectionDateTime } from "@/utils/attendanceCorrection"

const __ = inject("$translate")
const user = inject("$user")
const props = defineProps({
	id: {
		type: String,
		required: true,
	},
})
const rejectionReason = ref("")
const approvalError = ref("")

const doc = createDocumentResource({
	doctype: "Attendance Correction Request",
	name: props.id,
	auto: true,
})

const context = createResource({
	url: "hrms.api.attendance_correction.get_attendance_correction_context",
})

const approveResource = createResource({
	url: "hrms.api.attendance_correction.approve_attendance_correction_request",
})

const rejectResource = createResource({
	url: "hrms.api.attendance_correction.reject_attendance_correction_request",
})

const canApprove = computed(() => {
	if (doc.doc?.status !== "Pending") return false
	const roles = user?.data?.roles || []
	return (
		doc.doc?.approver === user?.data?.name ||
		user?.data?.name === "Administrator" ||
		roles.includes("HR Manager") ||
		roles.includes("System Manager")
	)
})

const rows = computed(() => [
	{ label: "Employee", value: doc.doc?.employee_name },
	{ label: "Attendance Date", value: doc.doc?.attendance_date },
	{ label: "Request Type", value: doc.doc?.request_type },
	{ label: "Log Type", value: doc.doc?.requested_log_type },
	{ label: "Requested Time", value: formatCorrectionDateTime(doc.doc?.requested_time) },
	{ label: "Status", value: doc.doc?.status },
	{ label: "Reason", value: doc.doc?.reason },
	{ label: "Result Attendance", value: doc.doc?.result_attendance },
])

watch(
	() => doc.doc,
	(value) => {
		if (!value?.attendance_date || !value?.employee) return
		context.fetch({ date: value.attendance_date, employee: value.employee })
	},
	{ immediate: true }
)

async function approve() {
	approvalError.value = ""
	await approveResource.submit({ name: props.id })
	await doc.reload()
	toast({
		title: __("Success"),
		text: __("Attendance correction request approved"),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
}

async function reject() {
	approvalError.value = ""
	if (!rejectionReason.value.trim()) {
		approvalError.value = __("Please enter a rejection reason")
		return
	}
	await rejectResource.submit({ name: props.id, reason: rejectionReason.value.trim() })
	await doc.reload()
	toast({
		title: __("Success"),
		text: __("Attendance correction request rejected"),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
}
</script>

<style scoped>
.correction-detail {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 100%;
	padding: 12px 16px 110px;
	background: #f1eee7;
}

.detail-surface,
.approval-actions {
	display: flex;
	flex-direction: column;
	gap: 12px;
	border: 1px solid #e3dfd4;
	border-radius: 8px;
	background: #fff;
	padding: 14px;
}

.detail-row {
	display: flex;
	justify-content: space-between;
	gap: 12px;
	font-size: 14px;
}

.detail-row span {
	color: #6b7280;
}

.detail-row strong {
	text-align: right;
	color: #111827;
	font-weight: 600;
}
</style>
