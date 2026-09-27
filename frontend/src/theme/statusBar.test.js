import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const srcDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..")
const frontendDir = path.resolve(srcDir, "..")

function read(relative) {
	return fs.readFileSync(path.join(frontendDir, relative), "utf8")
}

function tokenValue(block, name) {
	const match = block.match(new RegExp(`${name}:\\s*([^;]+);`))
	assert.ok(match, `${name} not found`)
	return match[1].trim().toLowerCase()
}

function pageColors() {
	const tokens = read("src/theme/home-tokens.css")
	const light = tokens.match(/:root\s*\{([\s\S]*?)\n\}/)[1]
	const dark = tokens.match(/\[data-theme="dark"\]\s*\{([\s\S]*?)\n\}/)[1]
	return { light: tokenValue(light, "--h-bg-page"), dark: tokenValue(dark, "--h-bg-page") }
}

function metaContent(html, name) {
	const match = html.match(new RegExp(`<meta\\s+name="${name}"\\s+content="([^"]*)"`))
	assert.ok(match, `meta ${name} not found`)
	return match[1]
}

// "white" is not a value iOS knows; only default, black and black-translucent
// exist. default keeps the status bar opaque, so iOS 27 has no transparent band
// to lay its Liquid Glass wash over.
test("the status bar style is the opaque default", () => {
	const html = read("index.html")
	assert.equal(metaContent(html, "apple-mobile-web-app-status-bar-style"), "default")
})

test("the viewport still extends under the home indicator", () => {
	const html = read("index.html")
	const content = html.match(/name="viewport"\s+content="([^"]*)"/)[1]
	const parts = content.split(",").map((part) => part.trim())
	assert.ok(parts.includes("viewport-fit=cover"), `viewport parts: ${parts.join(" | ")}`)
})

test("theme-color starts on the light page colour instead of pure white", () => {
	const html = read("index.html")
	assert.equal(metaContent(html, "theme-color").toLowerCase(), pageColors().light)
})

// The manifest used to carry a leftover brand blue that nothing on screen used.
test("the manifest colours match the light page", () => {
	const config = read("vite.config.js")
	const { light } = pageColors()
	assert.match(config, new RegExp(`theme_color:\\s*"${light}"`, "i"))
	assert.match(config, new RegExp(`background_color:\\s*"${light}"`, "i"))
})

// iOS 26+ samples the root background for the status bar. Ionic paints body a
// fixed #f4f5f6 in both themes, so the root has to be set explicitly and last.
test("the root background follows the header on screen", () => {
	const css = read("src/main.css")
	assert.match(css, /:root\s*\{[\s\S]*?--h-status-bar-bg:\s*#ffffff/i)
	assert.match(
		css,
		/:root:has\(\[data-status-bar="page"\]:not\(\.ion-page-hidden\):not\(\.ion-page-hidden \[data-status-bar="page"\]\)\)\s*\{[\s\S]*?--h-status-bar-bg:\s*var\(--h-bg-page\)/
	)
	assert.match(css, /html,\s*body\s*\{[\s\S]*?background-color:\s*var\(--h-status-bar-bg\)/)
})

// home-tokens.css fades background-color on every descendant of [data-theme],
// which catches body but not html. The two then disagree for 250ms after each
// theme or page switch, and iOS can sample the half-faded grey. body is covered
// by the app shell, so the fade was never visible anyway.
test("body switches colour instantly, in step with html", () => {
	const css = read("src/main.css")
	assert.match(css, /\[data-theme\] body\s*\{[\s\S]*?transition:\s*none/)
})

// The stylesheet order decides who wins over Ionic's body background.
test("main.css loads after Ionic's core styles", () => {
	const main = read("src/main.js")
	const coreAt = main.indexOf('import "@ionic/vue/css/core.css"')
	const mainCssAt = main.indexOf('import "./main.css"')
	assert.ok(coreAt > -1 && mainCssAt > -1)
	assert.ok(coreAt < mainCssAt, "main.css must be imported after Ionic core.css")
})

test("BaseLayout marks its page as theme-coloured at the top", () => {
	const layout = read("src/components/BaseLayout.vue")
	assert.match(layout, /<ion-page data-status-bar="page">/)
})
