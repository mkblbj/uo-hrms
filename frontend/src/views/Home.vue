<template>
	<BaseLayout>
		<template #header-actions>
			<HomeStatusChip />
		</template>
		<template #body>
			<div class="home-container">
				<CheckInPanel class="w-full flex-1" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import BaseLayout from "@/components/BaseLayout.vue"
import CheckInPanel from "@/components/CheckInPanel.vue"
import HomeStatusChip from "@/components/home/HomeStatusChip.vue"
</script>

<style scoped>
.home-container {
	display: flex;
	flex-direction: column;
	padding: 12px;
	min-height: calc(100vh - 110px);
	background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}
</style>
