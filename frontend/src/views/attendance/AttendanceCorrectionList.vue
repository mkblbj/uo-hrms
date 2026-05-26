<template>
	<BaseLayout :pageTitle="__('Attendance Corrections')" backRoute="/dashboard/attendance">
		<template #body>
			<div class="correction-list">
				<TabButtons :buttons="tabs" v-model="activeTab" />

				<router-link
					v-if="activeTab === 'mine'"
					:to="{ name: 'AttendanceCorrectionFormView' }"
					v-slot="{ navigate }"
				>
					<Button variant="solid" class="w-full py-5" @click="navigate">
						<template #prefix>
							<FeatherIcon name="plus" class="w-4" />
						</template>
						{{ __("New Correction Request") }}
					</Button>
				</router-link>

				<div v-if="visibleItems.length" class="rounded border border-[#e3dfd4] bg-white">
					<router-link
						v-for="item in visibleItems"
						:key="item.name"
						:to="{ name: 'AttendanceCorrectionDetailView', params: { id: item.name } }"
						class="block border-b p-3 last:border-b-0"
					>
						<AttendanceCorrectionItem :doc="item" :isTeamRequest="activeTab === 'approvals'" />
					</router-link>
				</div>

				<EmptyState v-else-if="!loading" :message="__('No attendance correction requests found')" />
				<div v-else class="flex items-center justify-center p-6">
					<LoadingIndicator class="h-6 w-6 text-gray-800" />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, ref, watch } from "vue"
import { Button, FeatherIcon, LoadingIndicator } from "frappe-ui"

import AttendanceCorrectionItem from "@/components/AttendanceCorrectionItem.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import TabButtons from "@/components/TabButtons.vue"
import {
	attendanceCorrectionApprovalCount,
	myAttendanceCorrectionRequests,
	pendingAttendanceCorrectionApprovals,
} from "@/data/attendance_correction"
import { buildAttendanceCorrectionTabs } from "@/utils/attendanceCorrection"

const __ = inject("$translate")
const activeTab = ref("mine")

const hasApprovals = computed(() => Boolean(attendanceCorrectionApprovalCount.data))
const tabs = computed(() =>
	buildAttendanceCorrectionTabs(hasApprovals.value, attendanceCorrectionApprovalCount.data || 0)
)
const visibleItems = computed(() =>
	activeTab.value === "approvals"
		? pendingAttendanceCorrectionApprovals.data || []
		: myAttendanceCorrectionRequests.data || []
)
const loading = computed(() =>
	activeTab.value === "approvals"
		? pendingAttendanceCorrectionApprovals.loading
		: myAttendanceCorrectionRequests.loading
)

watch(hasApprovals, (value) => {
	if (!value && activeTab.value === "approvals") activeTab.value = "mine"
})
</script>

<style scoped>
.correction-list {
	display: flex;
	flex-direction: column;
	gap: 12px;
	min-height: 100%;
	padding: 12px 16px 110px;
	background: #f1eee7;
}
</style>
