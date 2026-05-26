<template>
	<ListItem :isTeamRequest="isTeamRequest" :employee="doc.employee" :employeeName="doc.employee_name">
		<template #left>
			<AttendanceIcon class="h-5 w-5 text-gray-500" />
			<div class="flex min-w-0 flex-col items-start gap-1.5">
				<div class="truncate text-base font-normal text-gray-800">
					{{ __(doc.request_type) }}
				</div>
				<div class="text-xs font-normal text-gray-500">
					<span>{{ doc.attendance_date }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span>{{ doc.requested_log_type }}</span>
					<span class="whitespace-pre"> &middot; </span>
					<span>{{ formatCorrectionDateTime(doc.requested_time) }}</span>
				</div>
			</div>
		</template>
		<template #right>
			<Badge variant="outline" :theme="getCorrectionStatusTheme(doc.status)" :label="__(doc.status)" size="md" />
			<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" />
		</template>
	</ListItem>
</template>

<script setup>
import { inject } from "vue"
import { Badge, FeatherIcon } from "frappe-ui"

import AttendanceIcon from "@/components/icons/AttendanceIcon.vue"
import ListItem from "@/components/ListItem.vue"
import { formatCorrectionDateTime, getCorrectionStatusTheme } from "@/utils/attendanceCorrection"

const __ = inject("$translate")

defineProps({
	doc: {
		type: Object,
		required: true,
	},
	isTeamRequest: {
		type: Boolean,
		default: false,
	},
})
</script>
