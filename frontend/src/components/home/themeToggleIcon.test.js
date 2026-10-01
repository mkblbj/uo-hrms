import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const togglePath = path.resolve(currentDir, "ThemeToggle.vue")
const CENTER = 12

function readSunPath() {
	const source = fs.readFileSync(togglePath, "utf8")
	const paths = [...source.matchAll(/\sd="([^"]+)"/g)].map((match) => match[1])
	const sun = paths.find((d) => /a\s*3?\.?\d*\s+3?\.?\d*\s+0\s+1\s*1/.test(d) && d.split("M").length > 3)
	assert.ok(sun, "expected a sun path with multiple rays")
	return sun
}

// Walks the ray segments of an SVG path and returns each one in polar form
// around the icon centre. Relative commands accumulate, which is exactly how the
// old icon drifted: its diagonal rays inherited the end point of the previous
// segment instead of starting from a fresh absolute coordinate.
function parseRays(d) {
	const discIndex = d.search(/M[\d.]+ [\d.]+a/)
	const body = discIndex === -1 ? d : d.slice(0, discIndex)
	const tokens = body.match(/[MmLlHhVv][^MmLlHhVvAaZz]*/g) || []
	let x = 0
	let y = 0
	const rays = []

	for (const token of tokens) {
		const command = token[0]
		const numbers = (token.slice(1).match(/-?\d*\.?\d+/g) || []).map(Number)
		let start = null

		if (command === "M") {
			;[x, y] = numbers
			continue
		}
		if (command === "m") {
			x += numbers[0]
			y += numbers[1]
			continue
		}

		start = [x, y]
		if (command === "v") y += numbers[0]
		else if (command === "V") y = numbers[0]
		else if (command === "h") x += numbers[0]
		else if (command === "H") x = numbers[0]
		else if (command === "l") {
			x += numbers[0]
			y += numbers[1]
		} else if (command === "L") {
			;[x, y] = numbers
		}

		rays.push({ start: toPolar(start), end: toPolar([x, y]) })
	}

	return rays
}

function toPolar([px, py]) {
	const dx = px - CENTER
	const dy = py - CENTER
	let angle = (Math.atan2(dy, dx) * 180) / Math.PI
	if (angle < 0) angle += 360
	return { radius: Math.hypot(dx, dy), angle }
}

function round(value) {
	return Math.round(value * 100) / 100
}

test("sun icon draws eight rays", () => {
	assert.equal(parseRays(readSunPath()).length, 8)
})

// The old path put four rays at radius 10.83-12.25 while the other four sat at
// 8-9, so the diagonals floated far outside the disc.
test("sun rays all start and end at the same distance from the centre", () => {
	const rays = parseRays(readSunPath())
	const inner = [...new Set(rays.map((ray) => round(Math.min(ray.start.radius, ray.end.radius))))]
	const outer = [...new Set(rays.map((ray) => round(Math.max(ray.start.radius, ray.end.radius))))]

	assert.equal(inner.length, 1, `rays start at mixed radii: ${inner.join(", ")}`)
	assert.equal(outer.length, 1, `rays end at mixed radii: ${outer.join(", ")}`)
	assert.ok(outer[0] > inner[0], "rays must point outward")
})

// The old path aimed one ray at 331.7 degrees instead of 315, which is the
// visible tilt that made the sun look wrong.
test("sun rays sit on an even 45 degree wheel", () => {
	const rays = parseRays(readSunPath())
	const angles = rays.map((ray) => round(ray.start.angle)).sort((a, b) => a - b)

	angles.forEach((angle, index) => {
		const expected = index * 45
		assert.ok(
			Math.abs(angle - expected) < 0.5,
			`ray ${index} points at ${angle} degrees, expected about ${expected}`
		)
	})
})

test("sun rays clear the disc and stay inside the viewBox", () => {
	const rays = parseRays(readSunPath())
	const inner = Math.min(...rays.map((ray) => Math.min(ray.start.radius, ray.end.radius)))
	const outer = Math.max(...rays.map((ray) => Math.max(ray.start.radius, ray.end.radius)))

	assert.ok(inner > 3.75, `rays overlap the disc at radius ${round(inner)}`)
	assert.ok(outer <= 9.5, `rays reach radius ${round(outer)} and crowd the viewBox edge`)
})
