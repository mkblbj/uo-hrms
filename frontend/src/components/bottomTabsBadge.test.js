import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const srcDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const read = (relative) => fs.readFileSync(path.join(srcDir, relative), "utf8")

// Ionic's tab button clips its contents to the button box (.button-native has
// overflow: hidden). The unread badge sits above the icon's top-right corner and
// pokes over that edge, so its top was cut flat on the phone.
test("the tab buttons do not clip the unread badge", () => {
	const tabs = read("components/BottomTabs.vue")
	assert.match(tabs, /ion-tab-button::part\(native\)\s*\{[\s\S]*?overflow:\s*visible/)
})

// The clip exists for Material mode's tap ripple. The app pins Ionic to iOS mode
// on every platform, so there is no ripple to spill once the clip is lifted.
test("the app runs Ionic in iOS mode everywhere", () => {
	assert.match(read("utils/ionicConfig.js"), /const config = \{ mode: "ios" \}/)
})
