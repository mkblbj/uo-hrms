<template>
	<BaseLayout :pageTitle="pageTitle">
		<template #body>
			<div class="attendance-page">
				<AttendanceCorrectionEntryStrip />
				<AttendanceCalendar class="flex-1 min-h-0" />
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject } from "vue"
import AttendanceCorrectionEntryStrip from "@/components/AttendanceCorrectionEntryStrip.vue"
import BaseLayout from "@/components/BaseLayout.vue"
import AttendanceCalendar from "@/components/AttendanceCalendar.vue"

const __ = inject("$translate")

const pageTitle = computed(() => {
	const lang = frappe?.boot?.lang || "zh"
	if (lang === "ja") return "勤怠"
	if (lang === "zh") return "考勤"
	return __("Attendance")
})
</script>

<style scoped>
.attendance-page {
	display: flex;
	flex: 1;
	flex-direction: column;
	gap: 10px;
	min-height: 0;
	padding: 10px 16px 16px;
	background: var(--h-bg-page, #f1eee7);
}
</style>
