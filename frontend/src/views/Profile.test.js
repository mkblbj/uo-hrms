import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const profileSource = readFileSync(new URL("./Profile.vue", import.meta.url), "utf8")

test("always shows the Settings entry even when push notifications are unavailable", () => {
	assert.match(profileSource, /:to=\"\{ name: 'Settings' \}\"/)
	assert.doesNotMatch(profileSource, /<!-- Settings -->[\s\S]*v-if=\"allowPushNotifications\"/)
})
