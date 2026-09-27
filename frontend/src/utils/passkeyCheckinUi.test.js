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

test("scanner no longer opens a second camera stream for the torch", () => {
	const source = read("../components/QRScannerModal.vue")
	assert.ok(!source.includes("getUserMedia"), "getUserMedia should be gone")
	assert.match(source, /getRunningTrackCapabilities/)
	assert.match(source, /locationPromise/)
})

test("passkey manager lists devices and registers with optionsJSON", () => {
	const source = read("../components/PasskeyManager.vue")
	assert.match(source, /get_my_passkeys/)
	assert.match(source, /v-for="device in devices"/)
	assert.match(source, /startRegistration\(\{\s*optionsJSON/)
	assert.match(source, /Face ID \/ Fingerprint Check-in/)
})

test("server errors open the error sheet instead of only a toast", () => {
	const panel = read("../components/CheckInPanel.vue")
	assert.match(panel, /openPasskeySheet\("error"/)
	assert.match(panel, /:message="passkeySheet\.message"/)
	const sheet = read("../components/home/PasskeyCheckinSheet.vue")
	assert.match(sheet, /message:\s*{/)
})
