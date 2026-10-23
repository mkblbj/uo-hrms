import test from "node:test"
import assert from "node:assert/strict"
import {
	profileFormValues,
	profileSubmission,
	validateProfileForm,
	profileCollectionCopy,
} from "./profileCollection.js"

const profile = {
	employee: "EMP-001",
	employee_name: "张三",
	employee_number: "0001",
	cell_number: "09001234567",
	custom_wechat_id: "",
	current_address: "東京都\n302号室",
	contact_email: "staff@example.com",
	person_to_be_contacted: "李四",
	relation: "配偶",
	emergency_phone_number: "09000001234",
	modified: "2026-10-16 10:00:00.000000",
}

test("initial form values preserve phone and multiline address and exclude identity fields", () => {
	assert.deepEqual(profileFormValues(profile), {
		cell_number: "09001234567",
		custom_wechat_id: "",
		current_address: "東京都\n302号室",
		contact_email: "staff@example.com",
		person_to_be_contacted: "李四",
		relation: "配偶",
		emergency_phone_number: "09000001234",
	})
})

test("phone address and email are required but WeChat is optional", () => {
	assert.deepEqual(validateProfileForm(profileFormValues(profile)), {})
	const errors = validateProfileForm({
		...profileFormValues(profile),
		cell_number: " ",
		current_address: "\n",
		contact_email: "bad",
	})
	assert.deepEqual(Object.keys(errors).sort(), ["cell_number", "contact_email", "current_address"])
})

test("submission contains only seven contact fields and the loaded version", () => {
	const payload = profileSubmission(profile, {
		...profile,
		employee: "OTHER",
		user_id: "other@example.com",
		status: "Left",
		cell_number: " 09001234567 ",
	})
	assert.deepEqual(Object.keys(payload).sort(), [
		"cell_number",
		"contact_email",
		"current_address",
		"custom_wechat_id",
		"emergency_phone_number",
		"modified",
		"person_to_be_contacted",
		"relation",
	])
	assert.equal(payload.modified, profile.modified)
	assert.equal(payload.cell_number, "09001234567")
})

test("emergency contact name relationship and phone are required", () => {
	const errors = validateProfileForm({
		...profileFormValues(profile),
		person_to_be_contacted: " ",
		relation: "",
		emergency_phone_number: "\t",
	})
	assert.deepEqual(Object.keys(errors).sort(), [
		"emergency_phone_number",
		"person_to_be_contacted",
		"relation",
	])
})

test("copy uses the chosen language and Chinese fallback", () => {
	assert.equal(profileCollectionCopy("submit", "zh"), "确认并提交")
	assert.equal(profileCollectionCopy("submit", "ja"), "確認して送信")
	assert.equal(profileCollectionCopy("submit", "en"), "Confirm and Submit")
	assert.equal(profileCollectionCopy("submit", "unknown"), "确认并提交")
})
