<template>
	<div class="space-y-3 rounded border border-[#e3dfd4] bg-white p-3">
		<div class="flex items-center justify-between gap-3">
			<div class="text-sm font-semibold text-gray-900">{{ __("Day Context") }}</div>
			<div class="text-xs text-gray-500">{{ context?.attendance_date }}</div>
		</div>

		<div class="grid grid-cols-2 gap-2 text-sm">
			<div>
				<div class="text-xs text-gray-500">{{ __("Shift") }}</div>
				<div class="font-medium text-gray-800">{{ context?.shift || "-" }}</div>
			</div>
			<div>
				<div class="text-xs text-gray-500">{{ __("Attendance") }}</div>
				<div class="font-medium text-gray-800">{{ context?.attendance?.status || "-" }}</div>
			</div>
		</div>

		<div>
			<div class="mb-1 text-xs text-gray-500">{{ __("Check-ins") }}</div>
			<div v-if="context?.checkins?.length" class="space-y-1">
				<div
					v-for="checkin in context.checkins"
					:key="checkin.name"
					class="flex items-center justify-between gap-3 rounded bg-[#f8f6ef] px-2 py-1 text-sm"
				>
					<span class="font-medium text-gray-800">{{ checkin.log_type || "-" }}</span>
					<span class="text-gray-600">{{ formatCorrectionDateTime(checkin.time) }}</span>
				</div>
			</div>
			<div v-else class="text-sm text-gray-500">{{ __("No check-ins for this day") }}</div>
		</div>
	</div>
</template>

<script setup>
import { inject } from "vue"

import { formatCorrectionDateTime } from "@/utils/attendanceCorrection"

const __ = inject("$translate")

defineProps({
	context: {
		type: Object,
		default: null,
	},
})
</script>
