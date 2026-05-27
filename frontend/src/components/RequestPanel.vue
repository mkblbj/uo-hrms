<template>
	<div class="w-full">
		<TabButtons
			:buttons="TAB_BUTTONS"
			v-model="activeTab"
		/>
		<RequestList v-if="activeTab == 'My Requests'" :items="myRequests" />
		<RequestList
			v-else-if="activeTab == 'Team Requests'"
			:items="teamRequests"
			:teamRequests="true"
		/>
	</div>
</template>

<script setup>
import { ref, inject, onMounted, computed, markRaw } from "vue"

import TabButtons from "@/components/TabButtons.vue"
import RequestList from "@/components/RequestList.vue"

import {
	myAttendanceRequests,
	myCorrectionRequests,
	myShiftRequests,
	teamAttendanceRequests,
	teamCorrectionRequests,
	teamShiftRequests,
} from "@/data/attendance"
import { attendanceCorrectionApprovalCount } from "@/data/attendance_correction"
import { myClaims, teamClaims } from "@/data/claims"
import { myLeaves, teamLeaves } from "@/data/leaves"

import AttendanceCorrectionItem from "@/components/AttendanceCorrectionItem.vue"
import AttendanceRequestItem from "@/components/AttendanceRequestItem.vue"
import ExpenseClaimItem from "@/components/ExpenseClaimItem.vue"
import LeaveRequestItem from "@/components/LeaveRequestItem.vue"
import ShiftRequestItem from "@/components/ShiftRequestItem.vue"

import { useListUpdate } from "@/composables/realtime"

const activeTab = ref("My Requests")
const socket = inject("$socket")

const TAB_BUTTONS = ["My Requests", "Team Requests"] // __("My Requests"), __("Team Requests")

const myRequests = computed(() =>
	updateRequestDetails(myLeaves, myClaims, myShiftRequests, myAttendanceRequests, myCorrectionRequests)
)

const teamRequests = computed(() =>
	updateRequestDetails(teamLeaves, teamClaims, teamShiftRequests, teamAttendanceRequests, teamCorrectionRequests)
)

function updateRequestDetails(leaves, claims, shiftRequests, attendanceRequests, correctionRequests) {
	const requests = [leaves, claims, shiftRequests, attendanceRequests, correctionRequests].reduce(
		(acc, resource) => acc.concat(resource?.data || []),
		[]
	)

	const componentMap = {
		"Leave Application": LeaveRequestItem,
		"Expense Claim": ExpenseClaimItem,
		"Shift Request": ShiftRequestItem,
		"Attendance Request": AttendanceRequestItem,
		"Attendance Correction Request": AttendanceCorrectionItem,
	}
	requests.forEach((request) => {
		request.component = markRaw(componentMap[request.doctype])
	})

	return getSortedRequests(requests)
}

function getSortedRequests(list) {
	// return top 10 requests sorted by posting date
	return list
		.sort((a, b) => {
			return new Date(b.creation) - new Date(a.creation)
		})
		.splice(0, 10)
}

onMounted(() => {
	useListUpdate(socket, "Leave Application", () => teamLeaves.reload())
	useListUpdate(socket, "Expense Claim", () => teamClaims.reload())
	useListUpdate(socket, "Shift Request", () => teamShiftRequests.reload())
	useListUpdate(socket, "Attendance Request", () => teamAttendanceRequests.reload())
	useListUpdate(socket, "Attendance Correction Request", () => {
		myCorrectionRequests.reload()
		teamCorrectionRequests.reload()
		attendanceCorrectionApprovalCount.reload()
	})
})
</script>
