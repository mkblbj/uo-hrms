<template>
	<BaseLayout :pageTitle="copy('form.detailTitle')" :backRoute="backRoute">
		<template #body>
			<div v-if="doc.data" class="correction-detail">
				<AttendanceCorrectionContextPanel :context="doc.data.context" />
				<div class="detail-surface">
					<div v-for="row in rows" :key="row.label" class="detail-row">
						<span>{{ row.label }}</span>
						<template v-if="row.badge">
							<Badge
								variant="outline"
								:theme="row.badge.theme"
								:label="row.badge.label"
								size="md"
							/>
						</template>
						<strong v-else>{{ row.value || "-" }}</strong>
					</div>
					<div v-if="doc.data?.rejection_reason" class="detail-row">
						<span>{{ copy("field.rejectionReason") }}</span>
						<strong class="!text-red-600">{{ doc.data.rejection_reason }}</strong>
					</div>
				</div>

				<div v-if="canApprove" class="approval-actions">
					<FormField
						fieldtype="Small Text"
						fieldname="rejection_reason"
						v-model="rejectionReason"
						:label="copy('field.rejectionReason')"
					/>
					<ErrorMessage :message="approvalError || approveResource.error || rejectResource.error" />
					<div class="grid grid-cols-2 gap-3">
						<Button variant="subtle" theme="red" class="py-5" :loading="rejectResource.loading" @click="reject">
							{{ copy("action.reject") }}
						</Button>
						<Button variant="solid" theme="green" class="py-5" :loading="approveResource.loading" @click="approve">
							{{ copy("action.approve") }}
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
import { computed, inject, ref } from "vue"
import { Badge, Button, ErrorMessage, LoadingIndicator, createResource, toast } from "frappe-ui"
import { useRoute } from "vue-router"

import AttendanceCorrectionContextPanel from "@/components/AttendanceCorrectionContextPanel.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import FormField from "@/components/FormField.vue"
import {
	attendanceCorrectionApprovalCount,
	myAttendanceCorrectionRequests,
	pendingAttendanceCorrectionApprovals,
} from "@/data/attendance_correction"
import {
	formatCorrectionDateTime,
	getAttendanceCorrectionCopy,
	getCorrectionLang,
	getCorrectionStatusTheme,
} from "@/utils/attendanceCorrection"

const __ = inject("$translate")
const props = defineProps({
	id: {
		type: String,
		required: true,
	},
})
const route = useRoute()
const rejectionReason = ref("")
const approvalError = ref("")
const lang = computed(() => getCorrectionLang(globalThis.window?.frappe?.boot?.lang))
const copy = (key) => getAttendanceCorrectionCopy(key, lang.value)
const isApprovalMode = computed(() => route.query.mode === "approval")
const backRoute = computed(() =>
	isApprovalMode.value ? "/attendance-corrections?tab=approvals" : "/attendance-corrections"
)

const doc = createResource({
	url: "hrms.api.attendance_correction.get_attendance_correction_request",
	params: { name: props.id },
	auto: true,
})

const approveResource = createResource({
	url: "hrms.api.attendance_correction.approve_attendance_correction_request",
})

const rejectResource = createResource({
	url: "hrms.api.attendance_correction.reject_attendance_correction_request",
})

const canApprove = computed(() => {
	if (doc.data?.status !== "Pending") return false
	return Boolean(doc.data?.can_approve)
})

const rows = computed(() => [
	{ label: copy("field.employee"), value: doc.data?.employee_name },
	{ label: copy("field.attendanceDate"), value: doc.data?.attendance_date },
	{
		label: copy("field.requestType"),
		value: doc.data?.request_type ? copy(`requestType.${doc.data.request_type}`) : "",
	},
	{
		label: copy("field.logType"),
		value: doc.data?.requested_log_type ? copy(`logType.${doc.data.requested_log_type}`) : "",
	},
	{ label: copy("field.requestedTime"), value: formatCorrectionDateTime(doc.data?.requested_time, lang.value) },
	{
		label: copy("field.status"),
		badge: doc.data?.status
			? { theme: getCorrectionStatusTheme(doc.data.status), label: copy(`status.${doc.data.status}`) }
			: null,
		value: doc.data?.status ? copy(`status.${doc.data.status}`) : "",
	},
	{ label: copy("field.reason"), value: doc.data?.reason },
	...(doc.data?.result_attendance ? [{ label: copy("field.resultAttendance"), value: doc.data.result_attendance }] : []),
])

async function approve() {
	approvalError.value = ""
	await approveResource.submit({ name: props.id })
	await doc.reload()
	await reloadCorrectionResources()
	toast({
		title: __("Success"),
		text: copy("form.approved"),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
}

async function reject() {
	approvalError.value = ""
	if (!rejectionReason.value.trim()) {
		approvalError.value = copy("form.rejectionRequired")
		return
	}
	await rejectResource.submit({ name: props.id, reason: rejectionReason.value.trim() })
	await doc.reload()
	await reloadCorrectionResources()
	toast({
		title: __("Success"),
		text: copy("form.rejected"),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
}

async function reloadCorrectionResources() {
	await Promise.allSettled([
		myAttendanceCorrectionRequests.reload(),
		pendingAttendanceCorrectionApprovals.reload(),
		attendanceCorrectionApprovalCount.reload(),
	])
}
</script>

<style scoped>
.correction-detail {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 100%;
	padding: 12px 16px 110px;
	background: var(--h-bg-page, #f1eee7);
}

.detail-surface,
.approval-actions {
	display: flex;
	flex-direction: column;
	gap: 12px;
	border: 1px solid var(--h-bd-default, #e3dfd4);
	border-radius: 8px;
	background: var(--h-bg-card, #fff);
	padding: 14px;
}

.detail-row {
	display: flex;
	justify-content: space-between;
	gap: 12px;
	font-size: 14px;
}

.detail-row span {
	color: var(--h-fg-secondary, #6b7280);
}

.detail-row strong {
	text-align: right;
	color: var(--h-fg-primary, #111827);
	font-weight: 600;
}
</style>
