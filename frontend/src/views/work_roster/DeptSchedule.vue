<template>
	<BaseLayout :pageTitle="__('Department Schedule')" :backRoute="'/dashboard/work-roster'">
		<template #body>
			<div class="flex flex-col px-4 py-4 space-y-4">
				<div v-if="scheduleResource.loading" class="text-center py-10">
					<div class="text-gray-400">{{ __("Loading...") }}</div>
				</div>

				<template v-else>
					<div class="text-center">
						<div class="text-lg font-semibold text-gray-800">{{ __("Department Schedule") }}</div>
					</div>

					<!-- Employee Schedule Cards -->
					<div
						v-for="emp in employeeSchedules"
						:key="emp.employee"
						class="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
					>
						<div class="px-4 py-3 bg-gray-50 border-b border-gray-100">
							<div class="font-medium text-gray-800">{{ emp.employee_name }}</div>
							<div class="text-xs text-gray-500">
								{{ emp.entries.length }} {{ __("shifts") }} · {{ emp.totalHours.toFixed(1) }}h
							</div>
						</div>
						<div class="divide-y divide-gray-50">
							<div
								v-for="entry in emp.entries"
								:key="entry.name"
								class="flex items-center justify-between px-4 py-2"
							>
								<span class="text-sm text-gray-600">{{ formatDate(entry.date) }}</span>
								<span class="text-sm font-medium text-gray-800">
									{{ entry.wr_shift_slot || formatTimeRange(entry.custom_start_time, entry.custom_end_time) }}
								</span>
							</div>
						</div>
					</div>

					<div v-if="!employeeSchedules.length" class="text-center py-8">
						<div class="text-gray-400 text-sm">{{ __("No schedule data") }}</div>
					</div>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, onMounted } from "vue"
import { useRoute } from "vue-router"
import { createResource } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")
const route = useRoute()

const periodId = computed(() => route.params.periodId)

const scheduleResource = createResource({
	url: "work_roster.api.schedule.get_department_schedule",
	auto: false,
})

onMounted(() => {
	if (periodId.value) {
		scheduleResource.fetch({ params: { wr_period: periodId.value } })
	}
})

const employeeSchedules = computed(() => {
	const entries = scheduleResource.data || []
	const grouped = {}

	for (const e of entries) {
		if (!grouped[e.employee]) {
			grouped[e.employee] = {
				employee: e.employee,
				employee_name: e.employee_name,
				entries: [],
				totalHours: 0,
			}
		}
		grouped[e.employee].entries.push(e)
		grouped[e.employee].totalHours += e.hours || 0
	}

	return Object.values(grouped).sort((a, b) =>
		a.employee_name.localeCompare(b.employee_name)
	)
})

function formatDate(dateStr) {
	if (!dateStr) return ""
	return dayjs(dateStr).format("M/D (ddd)")
}

function formatTimeRange(start, end) {
	if (!start || !end) return __("Custom")
	return `${start.substring(0, 5)}-${end.substring(0, 5)}`
}
</script>
