import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs/promises"
import { fileURLToPath, pathToFileURL } from "node:url"
import path from "node:path"
import { parse, compileScript } from "@vue/compiler-sfc"
import { createSSRApp } from "vue"
import { renderToString } from "@vue/server-renderer"

async function render(props) {
	const filename = fileURLToPath(new URL("./AttendanceDayDetails.vue", import.meta.url))
	const { descriptor } = parse(await fs.readFile(filename, "utf8"), { filename })
	let code = compileScript(descriptor, {
		id: "attendance-detail-test",
		inlineTemplate: true,
	}).content
	code = code.replace(/from (["'])([^"']+)\1/g, (_, quote, name) => {
		const target = name.startsWith("@/")
			? pathToFileURL(path.resolve(path.dirname(filename), "../../", name.slice(2) + ".js")).href
			: import.meta.resolve(name)
		return `from ${JSON.stringify(target)}`
	})
	const { default: component } = await import(
		`data:text/javascript;base64,${Buffer.from(code).toString("base64")}`
	)
	return renderToString(createSSRApp(component, { lang: "zh", ...props }))
}

const details = {
	attendance_date: "2026-09-11",
	is_settled: true,
	working_hours: 5.5,
	completed_hours: 5.5,
	periods: [
		{
			in_time: "2026-09-11 08:55:51",
			out_time: "2026-09-11 12:12:59",
			counted_in_time: "2026-09-11 09:00:00",
			counted_out_time: "2026-09-11 12:00:00",
			lunch_deduction: 0,
			working_hours: 3,
		},
		{
			in_time: "2026-09-11 14:27:19",
			out_time: "2026-09-11 17:02:21",
			counted_in_time: "2026-09-11 14:30:00",
			counted_out_time: "2026-09-11 17:00:00",
			lunch_deduction: 0,
			working_hours: 2.5,
		},
	],
	checkins: [
		{ name: "one", time: "2026-09-11 08:55:51", log_type: "IN", included_in_calculation: true },
		{ name: "two", time: "2026-09-11 12:12:59", log_type: "OUT", included_in_calculation: true },
		{ name: "three", time: "2026-09-11 14:27:19", log_type: "IN", included_in_calculation: true },
		{ name: "four", time: "2026-09-11 17:02:21", log_type: "OUT", included_in_calculation: true },
	],
}

test("day details render all punches, both counted periods, and the stored total", async () => {
	const html = await render({ details })
	for (const time of ["08:55:51", "12:12:59", "14:27:19", "17:02:21", "09:00", "14:30"])
		assert.ok(html.includes(time), time)
	assert.match(html, /总工时/)
	assert.match(html, /5\.5/)
	assert.match(html, /第 1 段/)
	assert.match(html, /第 2 段/)
	assert.match(html, /2\.5/)
})

test("an open day shows completed work separately from its pending final total", async () => {
	const html = await render({
		details: {
			...details,
			is_settled: false,
			working_hours: null,
			completed_hours: 3,
			periods: details.periods.slice(0, 1),
			open_period: { in_time: "2026-09-11 14:27:19" },
		},
	})
	assert.match(html, /待结算/)
	assert.match(html, /已完成分段合计/)
	assert.match(html, /未签退/)
})

test("zero hours and an empty punch list are visible without looking pending", async () => {
	const html = await render({
		details: { ...details, working_hours: 0, completed_hours: 0, periods: [], checkins: [] },
	})
	assert.match(html, /0\s*<\/strong>/)
	assert.match(html, /当天没有打卡记录/)
	assert.doesNotMatch(html, /待结算/)
})

test("ignored correction punches remain in the full history with clear labels", async () => {
	const html = await render({
		details: {
			...details,
			checkins: [
				{
					name: "correction",
					time: "2026-09-12 00:30:00",
					log_type: "OUT",
					checkin_method: "Attendance Correction",
					included_in_calculation: false,
				},
			],
		},
	})
	assert.match(html, /9\/12 00:30:00/)
	assert.match(html, /补卡/)
	assert.match(html, /不计工时/)
})

test("a failed load offers a retry instead of showing stale punch data", async () => {
	const html = await render({ error: new Error("Failed") })
	assert.match(html, /加载打卡明细失败/)
	assert.match(html, /重试/)
	assert.doesNotMatch(html, /08:55/)
})

test("a short work period explains zero hours instead of displaying a reversed range", async () => {
	const html = await render({
		details: {
			...details,
			working_hours: 0,
			completed_hours: 0,
			periods: [
				{
					in_time: "2026-09-11 09:05:00",
					out_time: "2026-09-11 09:25:00",
					counted_in_time: "2026-09-11 09:30:00",
					counted_out_time: "2026-09-11 09:00:00",
					counted_time_empty: true,
					lunch_deduction: 0,
					working_hours: 0,
				},
			],
		},
	})
	assert.match(html, /取整后不足一个计时单位/)
})
