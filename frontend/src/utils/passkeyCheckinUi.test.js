import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const dir = path.dirname(fileURLToPath(import.meta.url))
const read = (relative) => fs.readFileSync(path.resolve(dir, relative), "utf8")

test("action bar has a passkey mode with a face icon and busy state", () => {
	const source = read("../components/home/HomeScanActionBar.vue")
	assert.match(source, /mode:\s*{/)
	assert.match(source, /busy:\s*{/)
	assert.match(source, /lucide-scan-face/)
	assert.match(source, /pickPasskeyCopy/)
})

test("check-in panel wires the passkey flow and the sheet", () => {
	const source = read("../components/CheckInPanel.vue")
	for (const needle of [
		"hrms.api.passkey.get_checkin_context",
		"runPasskeyCheckin",
		"<PasskeyCheckinSheet",
		':mode="checkinMode"',
		"handleCheckinSuccess",
		"shouldShowWifiTip",
	]) {
		assert.ok(source.includes(needle), needle)
	}
})

test("sheet renders content from getSheetContent", () => {
	const source = read("../components/home/PasskeyCheckinSheet.vue")
	assert.match(source, /getSheetContent/)
	assert.match(source, /emit\(['"]action['"], action\.id\)/)
})
