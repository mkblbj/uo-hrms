import test from "node:test"
import assert from "node:assert/strict"

import routes from "./work_roster.js"

test("legacy my schedule redirects to unified mine view", () => {
	const route = routes.find((item) => item.path === "/work-roster/my-schedule")
	assert.deepEqual(route.redirect(), {
		name: "WorkRosterDashboard",
		query: { view: "mine" },
	})
})

test("legacy department schedule preserves period only for safe resolution", () => {
	const route = routes.find((item) => item.path === "/work-roster/department-schedule/:periodId")
	assert.deepEqual(
		route.redirect({
			params: { periodId: "Production-2026-8" },
		}),
		{
			name: "WorkRosterDashboard",
			query: {
				view: "department",
				period: "Production-2026-8",
			},
		}
	)
})
