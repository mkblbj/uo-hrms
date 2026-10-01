import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const chatPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "Chat.vue")
const source = fs.readFileSync(chatPath, "utf8")
const template = source.slice(0, source.indexOf("<script"))

// Chat is a tab now. The bar left over from when it hung off the attendance page
// ("勤怠に戻る" — which actually went home) has no place there.
test("the chat tab has no back bar", () => {
	assert.doesNotMatch(template, /<ion-header/)
	assert.doesNotMatch(template, /router-link/)
	assert.doesNotMatch(source, /Back to attendance/)
	assert.doesNotMatch(source, /IonHeader/)
})

test("the chat tab still embeds Raven's direct messages", () => {
	assert.match(template, /<iframe[\s\S]*?src="\/raven\/dm-channel"/)
})

// iOS 26+ probes 8px below the top edge for a fixed or sticky element and extends
// its background into the status bar; with none it lays a blur over the top. The
// iframe can't be that element, so a thin sticky band in Raven's own surface
// colour sits above it and reads as part of Raven's top bar.
test("a sticky band in Raven's colour gives iOS a solid top edge", () => {
	assert.match(template, /class="chat-edge sticky top-0"[^>]*:style="\{ background: ravenSurface \}"/)
	assert.match(source, /\.chat-edge\s*\{[\s\S]*?height:\s*calc\(10px \+ var\(--ion-safe-area-top, 0px\)\)/)
})

test("the band follows Raven's theme live and cleans up after itself", () => {
	assert.match(source, /addEventListener\("storage"/)
	assert.match(source, /removeEventListener\("storage"/)
	assert.match(source, /prefers-color-scheme: dark/)
	assert.match(source, /removeEventListener\("change"/)
	assert.match(source, /onBeforeUnmount/)
})
