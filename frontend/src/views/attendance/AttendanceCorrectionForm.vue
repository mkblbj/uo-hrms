<template>
	<BaseLayout :pageTitle="__('New Correction Request')" backRoute="/attendance-corrections">
		<template #body>
			<div class="correction-form">
				<AttendanceCorrectionContextPanel :context="context.data" />

				<div class="form-surface">
					<FormField
						fieldtype="Date"
						fieldname="attendance_date"
						v-model="form.attendance_date"
						:label="__('Attendance Date')"
						:reqd="true"
					/>
					<FormField
						fieldtype="Select"
						fieldname="request_type"
						v-model="form.request_type"
						:label="__('Request Type')"
						:options="'Forgot Check-in\nForgot Check-out\nCorrect Checkin Time\nOther'"
						:reqd="true"
					/>
					<FormField
						fieldtype="Select"
						fieldname="requested_log_type"
						v-model="form.requested_log_type"
						:label="__('Log Type')"
						:options="'IN\nOUT'"
						:reqd="true"
					/>
					<FormField
						fieldtype="Datetime"
						fieldname="requested_time"
						v-model="form.requested_time"
						:label="__('Requested Time')"
						:reqd="true"
					/>
					<FormField
						v-if="form.request_type === 'Correct Checkin Time'"
						fieldtype="Link"
						fieldname="original_checkin"
						v-model="form.original_checkin"
						:label="__('Original Checkin')"
						options="Employee Checkin"
						:reqd="true"
					/>
					<FormField
						fieldtype="Small Text"
						fieldname="reason"
						v-model="form.reason"
						:label="__('Reason')"
						:reqd="true"
					/>
				</div>

				<div class="sticky-action">
					<ErrorMessage :message="errorMessage || submitResource.error" />
					<Button variant="solid" class="w-full py-5" :loading="submitResource.loading" @click="submit">
						{{ __("Submit") }}
					</Button>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject, reactive, ref, watch } from "vue"
import { Button, ErrorMessage, createResource, toast } from "frappe-ui"
import { useRoute, useRouter } from "vue-router"

import AttendanceCorrectionContextPanel from "@/components/AttendanceCorrectionContextPanel.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import FormField from "@/components/FormField.vue"
import { buildCorrectionPayload } from "@/utils/attendanceCorrection"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const route = useRoute()
const router = useRouter()
const today = dayjs().format("YYYY-MM-DD")
const routeDate = Array.isArray(route.query.date) ? route.query.date[0] : route.query.date
const initialDate = routeDate || today
const errorMessage = ref("")
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

watch(
	() => form.attendance_date,
	(date) => {
		context.fetch({ date })
		if (!form.requested_time) form.requested_time = `${date} 09:00:00`
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
		errorMessage.value = __("Please complete all required fields")
		return
	}
	if (payload.request_type === "Correct Checkin Time" && !payload.original_checkin) {
		errorMessage.value = __("Please select the original check-in")
		return
	}

	await submitResource.submit({ payload })
	toast({
		title: __("Success"),
		text: __("Attendance correction request submitted"),
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
