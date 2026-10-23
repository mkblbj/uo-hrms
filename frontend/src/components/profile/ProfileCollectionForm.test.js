import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs/promises"
import { fileURLToPath, pathToFileURL } from "node:url"
import { parse, compileScript } from "@vue/compiler-sfc"
import { createSSRApp } from "vue"
import { renderToString } from "@vue/server-renderer"

async function render(props = {}) {
	const filename = fileURLToPath(new URL("./ProfileCollectionForm.vue", import.meta.url))
	const { descriptor } = parse(await fs.readFile(filename, "utf8"), { filename })
	let code = compileScript(descriptor, {
		id: "profile-collection-form-test",
		inlineTemplate: true,
	}).content
	code = code.replace(/from (["'])([^"']+)\1/g, (_, quote, name) => {
		const target = name.startsWith("@/")
			? pathToFileURL(fileURLToPath(new URL(`../../${name.slice(2)}.js`, import.meta.url))).href
			: import.meta.resolve(name)
		return `from ${JSON.stringify(target)}`
	})
	const { default: component } = await import(
		`data:text/javascript;base64,${Buffer.from(code).toString("base64")}`
	)
	return renderToString(
		createSSRApp(component, {
			profile: {
				employee_name: "温刚",
				employee_number: "0044",
				cell_number: "09001234567",
				current_address: "東京都\n302",
				contact_email: "staff@example.com",
				person_to_be_contacted: "李四",
				relation: "配偶",
				emergency_phone_number: "09000001234",
			},
			lang: "zh",
			...props,
		})
	)
}

test("form shows contacts and emergency contact fields with read-only identity", async () => {
	const html = await render()
	for (const label of [
		"温刚",
		"0044",
		"手机号",
		"微信号（选填）",
		"联系邮箱",
		"现住址",
		"紧急联系人姓名",
		"亲属",
		"紧急联系电话",
		"确认并提交",
	])
		assert.ok(html.includes(label), label)
	for (const field of [
		"cell_number",
		"custom_wechat_id",
		"contact_email",
		"current_address",
		"person_to_be_contacted",
		"relation",
		"emergency_phone_number",
	])
		assert.ok(html.includes(`name="${field}"`))
	assert.ok(!html.includes('name="employee_name"'))
	assert.ok(!html.includes('name="employee_number"'))
	assert.ok(html.includes('value="09001234567"'))
	assert.ok(html.includes('autocomplete="street-address"'))
})

test("submitting disables editing and provides visible feedback", async () => {
	const html = await render({ submitting: true })
	assert.ok(html.includes("正在提交"))
	assert.ok(html.includes('aria-busy="true"'))
	assert.ok((html.match(/disabled/g) || []).length >= 8)
})

test("server failure is announced and entered values remain in the form", async () => {
	const html = await render({ error: "提交失败 <script>" })
	assert.ok(html.includes('role="alert"'))
	assert.ok(html.includes("提交失败 &lt;script&gt;"))
	assert.ok(html.includes('value="staff@example.com"'))
	assert.ok(html.includes('value="09001234567"'))
})
