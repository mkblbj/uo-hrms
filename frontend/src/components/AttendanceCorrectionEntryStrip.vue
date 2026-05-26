<template>
	<div class="correction-entry">
		<router-link :to="{ name: 'AttendanceCorrectionListView' }" class="entry-link">
			<span>{{ __("Correction Requests") }}</span>
			<FeatherIcon name="chevron-right" class="h-4 w-4" />
		</router-link>
		<router-link
			v-if="approvalCount.data"
			:to="{ name: 'AttendanceCorrectionListView', query: { tab: 'approvals' } }"
			class="approval-link"
		>
			<span>{{ __("Pending Approvals") }}</span>
			<strong>{{ approvalCount.data }}</strong>
		</router-link>
	</div>
</template>

<script setup>
import { inject } from "vue"
import { FeatherIcon } from "frappe-ui"

import { attendanceCorrectionApprovalCount as approvalCount } from "@/data/attendance_correction"

const __ = inject("$translate")
</script>

<style scoped>
.correction-entry {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 8px;
	align-items: center;
}

.entry-link,
.approval-link {
	display: flex;
	align-items: center;
	justify-content: space-between;
	min-height: 40px;
	border: 1px solid #e3dfd4;
	border-radius: 8px;
	background: #fff;
	padding: 0 12px;
	color: #1f2937;
	font-size: 14px;
	font-weight: 600;
}

.approval-link {
	gap: 8px;
	color: #b45309;
}

.approval-link strong {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 22px;
	height: 22px;
	border-radius: 999px;
	background: #fef3c7;
	font-size: 12px;
}
</style>
