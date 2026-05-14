import test from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import vm from "node:vm"
import { fileURLToPath } from "node:url"

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const hrmsAppRoot = path.resolve(currentDir, "../../..")
const audioHelperPath = path.join(hrmsAppRoot, "hrms/public/js/qr_display_audio.js")
const qrDisplayTemplatePath = path.join(hrmsAppRoot, "hrms/www/qr_display.html")

function createButton() {
	const listeners = new Map()
	const classes = new Set()

	return {
		textContent: "",
		title: "",
		attributes: {},
		classList: {
			toggle(className, enabled) {
				if (enabled) {
					classes.add(className)
				} else {
					classes.delete(className)
				}
			},
			contains(className) {
				return classes.has(className)
			},
		},
		addEventListener(type, callback) {
			listeners.set(type, callback)
		},
		setAttribute(name, value) {
			this.attributes[name] = String(value)
		},
		click() {
			const callback = listeners.get("click")
			return callback?.({ preventDefault() {} })
		},
	}
}

function createFakeAudioContextClass() {
	class FakeAudioNode {
		constructor(context) {
			this.context = context
		}

		connect(target) {
			return target
		}
	}

	class FakeOscillator extends FakeAudioNode {
		constructor(context) {
			super(context)
			this.type = ""
			this.frequency = {
				setValueAtTime: (value, time) => {
					context.events.push({ type: "frequency", value, time })
				},
			}
		}

		start(time) {
			this.context.events.push({ type: "start", time })
		}

		stop(time) {
			this.context.events.push({ type: "stop", time })
		}
	}

	class FakeGain extends FakeAudioNode {
		constructor(context) {
			super(context)
			this.gain = {
				setValueAtTime: (value, time) => {
					context.events.push({ type: "gain-set", value, time })
				},
				exponentialRampToValueAtTime: (value, time) => {
					context.events.push({ type: "gain-ramp", value, time })
				},
			}
		}
	}

	return class FakeAudioContext {
		static instances = []

		constructor() {
			this.currentTime = 10
			this.destination = {}
			this.events = []
			this.resumeCalls = 0
			this.state = "suspended"
			FakeAudioContext.instances.push(this)
		}

		resume() {
			this.resumeCalls += 1
			this.state = "running"
			return Promise.resolve()
		}

		createOscillator() {
			return new FakeOscillator(this)
		}

		createGain() {
			return new FakeGain(this)
		}
	}
}

function loadAudioModule(AudioContextClass = createFakeAudioContextClass()) {
	assert.ok(fs.existsSync(audioHelperPath), "QR display audio helper should exist")

	const sandbox = {
		AudioContext: AudioContextClass,
		console,
	}
	sandbox.window = sandbox
	sandbox.globalThis = sandbox

	vm.runInNewContext(fs.readFileSync(audioHelperPath, "utf8"), sandbox, {
		filename: audioHelperPath,
	})

	return {
		audioModule: sandbox.HRMSQRDisplayAudio,
		AudioContextClass,
	}
}

test("QR display audio controller stays silent until the user enables it", async () => {
	const button = createButton()
	const { audioModule, AudioContextClass } = loadAudioModule()
	const controller = audioModule.createController({ button })

	controller.init()
	assert.equal(controller.isEnabled(), false)
	assert.equal(button.textContent, "🔇")
	assert.equal(await controller.play("IN"), false)
	assert.equal(AudioContextClass.instances.length, 0)

	await button.click()

	assert.equal(controller.isEnabled(), true)
	assert.equal(button.textContent, "🔊")
	assert.equal(button.attributes["aria-pressed"], "true")
	assert.equal(AudioContextClass.instances.length, 1)
	assert.equal(AudioContextClass.instances[0].resumeCalls, 1)
	assert.ok(
		AudioContextClass.instances[0].events.some((event) => event.type === "start"),
		"enabling sound should play a short ready tone from the user gesture"
	)
})

test("QR display audio controller plays distinct check-in and check-out tones", async () => {
	const button = createButton()
	const { audioModule, AudioContextClass } = loadAudioModule()
	const controller = audioModule.createController({ button })

	controller.init()
	await button.click()
	AudioContextClass.instances[0].events.length = 0

	assert.equal(await controller.play("IN"), true)
	const checkinFrequencies = AudioContextClass.instances[0].events
		.filter((event) => event.type === "frequency")
		.map((event) => event.value)

	AudioContextClass.instances[0].events.length = 0

	assert.equal(await controller.play("OUT"), true)
	const checkoutFrequencies = AudioContextClass.instances[0].events
		.filter((event) => event.type === "frequency")
		.map((event) => event.value)

	assert.notDeepEqual(checkinFrequencies, checkoutFrequencies)
	assert.deepEqual(checkinFrequencies, [880, 1174.66])
	assert.deepEqual(checkoutFrequencies, [659.25, 523.25])
})

test("QR display page wires the sound toggle into check-in notifications", () => {
	const template = fs.readFileSync(qrDisplayTemplatePath, "utf8")

	assert.match(template, /id="sound-toggle"/)
	assert.match(template, /\/assets\/hrms\/js\/qr_display_audio\.js/)
	assert.match(template, /HRMSQRDisplayAudio\.createController/)
	assert.match(template, /qrAudio\.play\(data\.log_type\)/)
})
