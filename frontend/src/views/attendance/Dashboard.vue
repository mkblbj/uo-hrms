<template>
	<BaseLayout pageTitle="Attendance">
		<template #body>
			<div class="attendance-page">
				<AttendanceCalendar />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import BaseLayout from "@/components/BaseLayout.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"
</script>

<style scoped>
.attendance-page {
	display: flex;
	flex-direction: column;
	flex: 1;
	padding: 10px;
	background: #f5f5f5;
	overflow: hidden;
	min-height: 0;
}
</style>
