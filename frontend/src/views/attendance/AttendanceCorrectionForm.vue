<template>
	<BaseLayout :pageTitle="copy('form.newRequest')" backRoute="/attendance-corrections">
		<template #body>
			<div class="correction-form">
				<AttendanceCorrectionContextPanel :context="context.data" />

				<div class="form-surface">
					<FormField
						fieldtype="Date"
						fieldname="attendance_date"
						v-model="form.attendance_date"
						:label="copy('field.attendanceDate')"
						:reqd="true"
					/>
					<FormField
						fieldtype="Select"
						fieldname="request_type"
						v-model="form.request_type"
						:label="copy('field.requestType')"
						:documentList="requestTypeOptions"
						:options="'Forgot Check-in\nForgot Check-out\nCorrect Checkin Time\nOther'"
						:hideSearch="true"
						:reqd="true"
					/>
					<FormField
						fieldtype="Select"
						fieldname="requested_log_type"
						v-model="form.requested_log_type"
						:label="copy('field.logType')"
						:documentList="logTypeOptions"
						:options="'IN\nOUT'"
						:hideSearch="true"
						:reqd="true"
					/>
					<FormField
						fieldtype="Datetime"
						fieldname="requested_time"
						v-model="form.requested_time"
						:label="copy('field.requestedTime')"
						:dateTimeFormatter="dateTimeFormatter"
						:nativeDateTime="true"
						:toNativeDateTimeValue="toNativeDateTimeInputValue"
						:fromNativeDateTimeValue="fromNativeDateTimeInputValue"
						:reqd="true"
					/>
					<FormField
						v-if="form.request_type === 'Correct Checkin Time'"
						fieldtype="Link"
						fieldname="original_checkin"
						v-model="form.original_checkin"
						:label="copy('field.originalCheckin')"
						:documentList="originalCheckinOptions"
						:placeholder="copy('field.originalCheckinPlaceholder')"
						:hideSearch="true"
						:reqd="true"
					/>
					<FormField
						fieldtype="Small Text"
						fieldname="reason"
						v-model="form.reason"
						:label="copy('field.reason')"
						:placeholder="copy('field.reasonPlaceholder')"
						:reqd="true"
					/>
				</div>

				<div class="sticky-action">
					<ErrorMessage :message="errorMessage || submitResource.error" />
					<Button variant="solid" class="w-full py-5" :loading="submitResource.loading" @click="submit">
						{{ copy("form.submit") }}
					</Button>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, reactive, ref, watch } from "vue"
import { Button, ErrorMessage, createResource, toast } from "frappe-ui"
import { useRoute, useRouter } from "vue-router"

import AttendanceCorrectionContextPanel from "@/components/AttendanceCorrectionContextPanel.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import FormField from "@/components/FormField.vue"
import {
	attendanceCorrectionApprovalCount,
	myAttendanceCorrectionRequests,
	pendingAttendanceCorrectionApprovals,
} from "@/data/attendance_correction"
import {
	buildCorrectionPayload,
	buildOriginalCheckinOptions,
	formatCorrectionDateTime,
	fromNativeDateTimeInputValue,
	getAttendanceCorrectionCopy,
	getCorrectionLang,
	toNativeDateTimeInputValue,
} from "@/utils/attendanceCorrection"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const route = useRoute()
const router = useRouter()
const today = dayjs().format("YYYY-MM-DD")
const routeDate = Array.isArray(route.query.date) ? route.query.date[0] : route.query.date
const initialDate = routeDate || today
const errorMessage = ref("")
const lang = computed(() => getCorrectionLang(globalThis.window?.frappe?.boot?.lang))
const copy = (key) => getAttendanceCorrectionCopy(key, lang.value)
const form = reactive({
	attendance_date: initialDate,
	request_type: "Forgot Check-in",
	requested_log_type: "IN",
	requested_time: `${initialDate} 09:00:00`,
	original_checkin: null,
	reason: "",
})

const context = createResource({
	url: "hrms.api.attendance_correction.get_attendance_correction_context",
	params: { date: form.attendance_date },
	auto: true,
})

const submitResource = createResource({
	url: "hrms.api.attendance_correction.submit_attendance_correction_request",
})

const requestTypeOptions = computed(() =>
	["Forgot Check-in", "Forgot Check-out", "Correct Checkin Time", "Other"].map((value) => ({
		label: getAttendanceCorrectionCopy(`requestType.${value}`, lang.value),
		value,
	}))
)

const logTypeOptions = computed(() =>
	["IN", "OUT"].map((value) => ({
		label: getAttendanceCorrectionCopy(`logType.${value}`, lang.value),
		value,
	}))
)

const originalCheckinOptions = computed(() =>
	buildOriginalCheckinOptions(context.data?.checkins || [], lang.value)
)

const dateTimeFormatter = (value) => formatCorrectionDateTime(value, lang.value)

watch(
	() => form.attendance_date,
	(date, oldDate) => {
		form.original_checkin = null
		if (!date) return

		context.fetch({ date })
		const currentTime = String(form.requested_time || "")
		if (!currentTime) {
			form.requested_time = `${date} 09:00:00`
		} else if (
			oldDate &&
			(currentTime.startsWith(`${oldDate} `) || currentTime.startsWith(`${oldDate}T`))
		) {
			form.requested_time = `${date}${currentTime.slice(String(oldDate).length)}`
		}
	}
)

async function submit() {
	errorMessage.value = ""
	const payload = buildCorrectionPayload(form)
	if (
		!payload.attendance_date ||
		!payload.request_type ||
		!payload.requested_log_type ||
		!payload.requested_time ||
		!payload.reason
	) {
		errorMessage.value = copy("form.completeRequired")
		return
	}
	if (payload.request_type === "Correct Checkin Time" && !payload.original_checkin) {
		errorMessage.value = copy("form.selectOriginal")
		return
	}

	await submitResource.submit({ payload })
	await Promise.allSettled([
		myAttendanceCorrectionRequests.reload(),
		pendingAttendanceCorrectionApprovals.reload(),
		attendanceCorrectionApprovalCount.reload(),
	])
	toast({
		title: __("Success"),
		text: copy("form.submitted"),
		icon: "check-circle",
		position: "bottom-center",
		iconClasses: "text-green-500",
	})
	router.replace({ name: "AttendanceCorrectionListView" })
}
</script>

<style scoped>
.correction-form {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 100%;
	padding: 12px 16px 110px;
	background: #f1eee7;
}

.form-surface {
	display: flex;
	flex-direction: column;
	gap: 14px;
	border: 1px solid #e3dfd4;
	border-radius: 8px;
	background: #fff;
	padding: 14px;
}

.sticky-action {
	position: sticky;
	bottom: 0;
	display: flex;
	flex-direction: column;
	gap: 8px;
	background: #f1eee7;
	padding-top: 8px;
}
</style>
