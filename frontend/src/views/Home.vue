<template>
	<BaseLayout>
		<template #header-actions>
			<HomeStatusChip :work-status="workStatus" />
		</template>
		<template #body>
			<div class="home-container">
				<CheckInPanel class="w-full flex-1" :work-status="workStatus" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { onBeforeUnmount, onMounted } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import CheckInPanel from "@/components/CheckInPanel.vue"
import HomeStatusChip from "@/components/home/HomeStatusChip.vue"
import { bindCheckinStatusRefresh } from "@/utils/homeExperience"

const workStatus = createResource({
	url: "hrms.api.get_employee_work_status",
	auto: true,
	cache: false,
})

const reloadWorkStatus = () => workStatus.reload()

let refreshInterval = null
let unbindCheckinStatusRefresh = () => {}

onMounted(() => {
	unbindCheckinStatusRefresh = bindCheckinStatusRefresh(window, reloadWorkStatus)
	refreshInterval = setInterval(reloadWorkStatus, 30000)
})

onBeforeUnmount(() => {
	unbindCheckinStatusRefresh()
	unbindCheckinStatusRefresh = () => {}
	if (refreshInterval) {
		clearInterval(refreshInterval)
		refreshInterval = null
	}
})
</script>

<style scoped>
.home-container {
	display: flex;
	flex-direction: column;
	padding: 12px 16px 20px;
	min-height: calc(100vh - 110px);
	background: #f1eee7;
}
</style>
