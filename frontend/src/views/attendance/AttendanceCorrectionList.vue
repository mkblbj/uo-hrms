<template>
	<BaseLayout :pageTitle="copy('form.listTitle')" backRoute="/dashboard/attendance">
		<template #body>
			<div class="correction-list">
				<TabButtons v-if="tabs.length > 1" :buttons="tabs" v-model="activeTab" />

				<router-link
					v-if="activeTab === 'mine'"
					:to="{ name: 'AttendanceCorrectionFormView' }"
					v-slot="{ navigate }"
				>
					<Button variant="outline" theme="gray" class="w-full py-5" @click="navigate">
						<template #prefix>
							<FeatherIcon name="plus" class="w-4" />
						</template>
						{{ copy("form.newRequest") }}
					</Button>
				</router-link>

				<div v-if="visibleItems.length" class="rounded border border-[#e3dfd4] bg-white">
					<router-link
						v-for="item in visibleItems"
						:key="item.name"
						:to="getDetailRoute(item)"
						class="block border-b p-3 last:border-b-0"
					>
						<AttendanceCorrectionItem :doc="item" :isTeamRequest="activeTab === 'approvals'" />
					</router-link>
				</div>

				<EmptyState v-else-if="!loading" :message="copy('form.empty')" />
				<div v-else class="flex items-center justify-center p-6">
					<LoadingIndicator class="h-6 w-6 text-gray-800" />
				</div>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, ref, watch } from "vue"
import { onIonViewWillEnter } from "@ionic/vue"
import { Button, FeatherIcon, LoadingIndicator } from "frappe-ui"
import { useRoute } from "vue-router"

import AttendanceCorrectionItem from "@/components/AttendanceCorrectionItem.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import EmptyState from "@/components/EmptyState.vue"
import TabButtons from "@/components/TabButtons.vue"
import {
	attendanceCorrectionApprovalCount,
	myAttendanceCorrectionRequests,
	pendingAttendanceCorrectionApprovals,
} from "@/data/attendance_correction"
import {
	buildAttendanceCorrectionTabs,
	getAttendanceCorrectionCopy,
	getCorrectionLang,
} from "@/utils/attendanceCorrection"

const route = useRoute()
const lang = computed(() => getCorrectionLang(globalThis.window?.frappe?.boot?.lang))
const copy = (key) => getAttendanceCorrectionCopy(key, lang.value)
const activeTab = ref(route.query.tab === "approvals" ? "approvals" : "mine")

const hasApprovals = computed(() => Boolean(attendanceCorrectionApprovalCount.data))
const approvalCountLoaded = computed(() => !attendanceCorrectionApprovalCount.loading)
const tabs = computed(() =>
	buildAttendanceCorrectionTabs(hasApprovals.value, attendanceCorrectionApprovalCount.data || 0, lang.value)
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

watch(
	() => route.query.tab,
	(tab) => {
		if (tab === "approvals") activeTab.value = "approvals"
		else if (tab === "mine") activeTab.value = "mine"
	}
)

watch([approvalCountLoaded, hasApprovals], ([loaded, hasApprovalItems]) => {
	if (loaded && !hasApprovalItems && activeTab.value === "approvals") activeTab.value = "mine"
})

function reloadCorrectionResources() {
	myAttendanceCorrectionRequests.reload()
	pendingAttendanceCorrectionApprovals.reload()
	attendanceCorrectionApprovalCount.reload()
}

function getDetailRoute(item) {
	return {
		name: "AttendanceCorrectionDetailView",
		params: { id: item.name },
		query: activeTab.value === "approvals" ? { mode: "approval" } : {},
	}
}

onIonViewWillEnter(() => {
	reloadCorrectionResources()
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
