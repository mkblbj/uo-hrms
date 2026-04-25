const routes = [
	{
		name: "PreferenceSubmitView",
		path: "/work-roster/preference/:periodId",
		props: true,
		component: () => import("@/views/work_roster/PreferenceSubmit.vue"),
	},
	{
		name: "MyScheduleView",
		path: "/work-roster/my-schedule",
		component: () => import("@/views/work_roster/MySchedule.vue"),
	},
	{
		name: "DeptScheduleView",
		path: "/work-roster/department-schedule/:periodId",
		props: true,
		component: () => import("@/views/work_roster/DeptSchedule.vue"),
	},
]

export default routes
