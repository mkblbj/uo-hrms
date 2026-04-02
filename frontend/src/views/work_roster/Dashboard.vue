<template>
	<BaseLayout :pageTitle="__('Work Roster')">
		<template #body>
			<div class="flex flex-col items-center mt-4 mb-7 py-4 px-4 space-y-5">
				<div v-if="dashboardData.loading" class="w-full text-center py-10">
					<div class="text-gray-400">{{ __("Loading...") }}</div>
				</div>

				<div v-else-if="dashboardData.data?.error === 'no_employee'" class="w-full text-center py-10">
					<div class="text-gray-500">{{ __("No employee record found") }}</div>
				</div>

				<template v-else-if="dashboardData.data">
					<div
						v-for="period in dashboardData.data.periods"
						:key="period.name"
						class="w-full bg-white rounded-xl shadow-sm p-4 border border-gray-100"
					>
						<div class="flex items-center justify-between mb-3">
							<div>
								<div class="text-base font-semibold text-gray-800">{{ period.title }}</div>
								<StatusBadge :status="period.status" />
							</div>
						</div>

						<div v-if="period.status === 'Collecting'" class="space-y-3">
							<div class="text-sm text-gray-600">
								{{ __("Deadline") }}: {{ formatDate(period.preference_deadline) }}
							</div>
							<div class="flex items-center gap-2">
								<span
									:class="period.has_preference ? 'text-green-600' : 'text-orange-500'"
									class="text-sm font-medium"
								>
									{{ period.has_preference ? __("Submitted") : __("Not Submitted") }}
								</span>
							</div>
							<router-link
								:to="`/work-roster/preference/${period.name}`"
								v-slot="{ navigate }"
							>
								<Button
									@click="navigate"
									:variant="period.has_preference ? 'subtle' : 'solid'"
									class="py-3 text-sm w-full"
								>
									{{ period.has_preference ? __("Edit Preference") : __("Submit Preference") }}
								</Button>
							</router-link>
						</div>

						<div v-else-if="period.status === 'Published'" class="space-y-3">
							<div v-if="period.upcoming_entries?.length" class="space-y-1.5">
								<div class="text-sm font-medium text-gray-700">{{ __("Upcoming Shifts") }}</div>
								<div
									v-for="entry in period.upcoming_entries"
									:key="entry.date"
									class="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
								>
									<span class="text-gray-600">{{ formatDate(entry.date) }}</span>
									<span class="font-medium text-gray-800">{{ entry.wr_shift_slot || __("Custom") }}</span>
								</div>
							</div>
							<div class="flex gap-2">
								<router-link
									to="/work-roster/my-schedule"
									v-slot="{ navigate }"
									class="flex-1"
								>
									<Button @click="navigate" variant="subtle" class="py-3 text-sm w-full">
										{{ __("My Schedule") }}
									</Button>
								</router-link>
								<router-link
									:to="`/work-roster/department-schedule/${period.name}`"
									v-slot="{ navigate }"
									class="flex-1"
								>
									<Button @click="navigate" variant="outline" class="py-3 text-sm w-full">
										{{ __("Dept Schedule") }}
									</Button>
								</router-link>
							</div>
						</div>

						<div v-else-if="period.status === 'Scheduling'" class="text-sm text-gray-500 py-2">
							{{ __("Schedule is being prepared...") }}
						</div>
					</div>

					<div v-if="!dashboardData.data.periods?.length" class="w-full text-center py-10">
						<div class="text-gray-400 text-sm">{{ __("No active roster periods") }}</div>
					</div>
				</template>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import { inject } from "vue"
import { createResource, Button } from "frappe-ui"
import BaseLayout from "@/components/BaseLayout.vue"
import StatusBadge from "@/components/work_roster/StatusBadge.vue"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const dashboardData = createResource({
	url: "work_roster.api.schedule.get_dashboard_data",
	auto: true,
	cache: "wr:dashboard",
})

function formatDate(dateStr) {
	if (!dateStr) return ""
	return dayjs(dateStr).format("M/D (ddd)")
}
</script>
