<template>
	<div class="space-y-3 rounded border p-3" style="background: var(--h-bg-card); border-color: var(--h-bd-default)">
		<div class="flex items-center justify-between gap-3">
			<div class="text-sm font-semibold" style="color: var(--h-fg-primary)">{{ copy("context.title") }}</div>
			<div class="text-xs" style="color: var(--h-fg-secondary)">{{ context?.attendance_date }}</div>
		</div>

		<div class="grid grid-cols-2 gap-2 text-sm">
			<div>
				<div class="text-xs" style="color: var(--h-fg-secondary)">{{ copy("context.shift") }}</div>
				<div class="font-medium" style="color: var(--h-fg-primary)">{{ context?.shift || "-" }}</div>
			</div>
			<div>
				<div class="text-xs" style="color: var(--h-fg-secondary)">{{ copy("context.attendance") }}</div>
				<div class="font-medium" style="color: var(--h-fg-primary)">
					{{
						context?.attendance?.status
							? copy(`attendanceStatus.${context.attendance.status}`)
							: "-"
					}}
				</div>
			</div>
		</div>

		<div>
			<div class="mb-1 text-xs" style="color: var(--h-fg-secondary)">{{ copy("context.checkins") }}</div>
			<div v-if="context?.checkins?.length" class="space-y-1">
				<div
					v-for="checkin in context.checkins"
					:key="checkin.name"
					class="flex items-center justify-between gap-3 rounded px-2 py-1 text-sm"
					style="background: var(--h-bg-card-inner)"
				>
					<span class="font-medium" style="color: var(--h-fg-primary)">
						{{ checkin.log_type ? copy(`logType.${checkin.log_type}`) : "-" }}
					</span>
					<span style="color: var(--h-fg-secondary)">{{ formatCorrectionDateTime(checkin.time, lang) }}</span>
				</div>
			</div>
			<div v-else class="text-sm" style="color: var(--h-fg-secondary)">{{ copy("context.empty") }}</div>
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
