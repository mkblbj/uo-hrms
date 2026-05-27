<template>
	<router-link :to="correctionRoute" class="correction-entry">
		<div class="entry-left">
			<div class="entry-icon">
				<FeatherIcon name="edit-3" class="h-4 w-4" />
			</div>
			<span class="entry-label">{{ copy("tabs.mine") }}</span>
		</div>
		<div class="entry-right">
			<span v-if="approvalCount.data" class="approval-badge">{{ approvalCount.data }}</span>
			<FeatherIcon name="chevron-right" class="h-4 w-4 text-gray-400" />
		</div>
	</router-link>
</template>

<script setup>
import { computed } from "vue"
import { FeatherIcon } from "frappe-ui"

import { attendanceCorrectionApprovalCount as approvalCount } from "@/data/attendance_correction"
import { getAttendanceCorrectionCopy, getCorrectionLang } from "@/utils/attendanceCorrection"

const lang = computed(() => getCorrectionLang(globalThis.window?.frappe?.boot?.lang))
const copy = (key) => getAttendanceCorrectionCopy(key, lang.value)

const correctionRoute = computed(() =>
	approvalCount.data
		? { name: "AttendanceCorrectionListView", query: { tab: "approvals" } }
		: { name: "AttendanceCorrectionListView" }
)
</script>

<style scoped>
.correction-entry {
	display: flex;
	align-items: center;
	justify-content: space-between;
	min-height: 44px;
	border: 1px solid #e3dfd4;
	border-radius: 10px;
	background: #fff;
	padding: 0 14px;
	color: #1f2937;
	font-size: 14px;
	font-weight: 600;
	transition: background 0.15s;
}

.correction-entry:active {
	background: #f8f6ef;
}

.entry-left {
	display: flex;
	align-items: center;
	gap: 10px;
}

.entry-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 28px;
	height: 28px;
	border-radius: 7px;
	background: #eef2ff;
	color: #4f46e5;
}

.entry-right {
	display: flex;
	align-items: center;
	gap: 8px;
}

.approval-badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 20px;
	height: 20px;
	border-radius: 999px;
	background: #fef3c7;
	color: #b45309;
	font-size: 12px;
	font-weight: 700;
	padding: 0 6px;
}
</style>
