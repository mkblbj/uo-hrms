const routes = [
	{
		name: "PreferenceSubmitView",
		path: "/work-roster/preference/:periodId",
		props: true,
		component: () => import("@/views/work_roster/PreferenceSubmit.vue"),
	},
	{
		path: "/work-roster/my-schedule",
		redirect: () => ({
			name: "WorkRosterDashboard",
			query: { view: "mine" },
		}),
	},
	{
		path: "/work-roster/department-schedule/:periodId",
		redirect: (to) => ({
			name: "WorkRosterDashboard",
			query: {
				view: "department",
				period: String(to.params.periodId || ""),
			},
		}),
	},
]

export default routes
