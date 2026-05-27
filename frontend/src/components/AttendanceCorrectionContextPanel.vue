<template>
	<div class="space-y-3 rounded border border-[#e3dfd4] bg-white p-3">
		<div class="flex items-center justify-between gap-3">
			<div class="text-sm font-semibold text-gray-900">{{ copy("context.title") }}</div>
			<div class="text-xs text-gray-500">{{ context?.attendance_date }}</div>
		</div>

		<div class="grid grid-cols-2 gap-2 text-sm">
			<div>
				<div class="text-xs text-gray-500">{{ copy("context.shift") }}</div>
				<div class="font-medium text-gray-800">{{ context?.shift || "-" }}</div>
			</div>
			<div>
				<div class="text-xs text-gray-500">{{ copy("context.attendance") }}</div>
				<div class="font-medium text-gray-800">
					{{
						context?.attendance?.status
							? copy(`attendanceStatus.${context.attendance.status}`)
							: "-"
					}}
				</div>
			</div>
		</div>

		<div>
			<div class="mb-1 text-xs text-gray-500">{{ copy("context.checkins") }}</div>
			<div v-if="context?.checkins?.length" class="space-y-1">
				<div
					v-for="checkin in context.checkins"
					:key="checkin.name"
					class="flex items-center justify-between gap-3 rounded bg-[#f8f6ef] px-2 py-1 text-sm"
				>
					<span class="font-medium text-gray-800">
						{{ checkin.log_type ? copy(`logType.${checkin.log_type}`) : "-" }}
					</span>
					<span class="text-gray-600">{{ formatCorrectionDateTime(checkin.time, lang) }}</span>
				</div>
			</div>
			<div v-else class="text-sm text-gray-500">{{ copy("context.empty") }}</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

import {
	formatCorrectionDateTime,
	getAttendanceCorrectionCopy,
	getCorrectionLang,
} from "@/utils/attendanceCorrection"

const lang = computed(() => getCorrectionLang(globalThis.window?.frappe?.boot?.lang))
const copy = (key) => getAttendanceCorrectionCopy(key, lang.value)

defineProps({
	context: {
		type: Object,
		default: null,
	},
})
</script>
