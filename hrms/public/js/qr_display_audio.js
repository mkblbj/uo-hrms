(function(global) {
	"use strict";

	const LABELS = {
		disabled: "提示音を有効にする",
		enabled: "提示音を無効にする",
	};
	const PROFILES = {
		READY: [{ frequency: 740, duration: 0.08, offset: 0 }],
		IN: [
			{ frequency: 880, duration: 0.11, offset: 0 },
			{ frequency: 1174.66, duration: 0.16, offset: 0.1 },
		],
		OUT: [
			{ frequency: 659.25, duration: 0.12, offset: 0 },
			{ frequency: 523.25, duration: 0.18, offset: 0.11 },
		],
	};

	function getAudioContextClass(options) {
		return options.AudioContextClass || global.AudioContext || global.webkitAudioContext || null;
	}

	function updateButton(button, enabled) {
		if (!button) return;

		const label = enabled ? LABELS.enabled : LABELS.disabled;
		button.textContent = enabled ? "🔊" : "🔇";
		button.title = label;
		button.setAttribute("aria-label", label);
		button.setAttribute("aria-pressed", String(enabled));
		button.classList.toggle("is-enabled", enabled);
	}

	function createController(options) {
		const resolvedOptions = options || {};
		const button = resolvedOptions.button || null;
		const AudioContextClass = getAudioContextClass(resolvedOptions);
		let audioContext = null;
		let enabled = false;

		function init() {
			updateButton(button, enabled);
			if (button) {
				button.addEventListener("click", function(event) {
					event.preventDefault();
					return toggle();
				});
			}
		}

		function isEnabled() {
			return enabled;
		}

		async function ensureAudioContext() {
			if (!AudioContextClass) return null;
			if (!audioContext) {
				audioContext = new AudioContextClass();
			}
			if (audioContext.state === "suspended" && typeof audioContext.resume === "function") {
				await audioContext.resume();
			}
			return audioContext;
		}

		function scheduleTone(context, tone, baseTime) {
			const oscillator = context.createOscillator();
			const gain = context.createGain();
			const startTime = baseTime + tone.offset;
			const endTime = startTime + tone.duration;

			oscillator.type = "sine";
			oscillator.frequency.setValueAtTime(tone.frequency, startTime);
			gain.gain.setValueAtTime(0.0001, startTime);
			gain.gain.exponentialRampToValueAtTime(0.18, startTime + 0.012);
			gain.gain.exponentialRampToValueAtTime(0.0001, endTime);
			oscillator.connect(gain).connect(context.destination);
			oscillator.start(startTime);
			oscillator.stop(endTime + 0.02);
		}

		async function playProfile(profileKey) {
			const profile = PROFILES[profileKey] || PROFILES.IN;
			const context = await ensureAudioContext();
			if (!context) return false;

			const baseTime = context.currentTime + 0.02;
			profile.forEach(function(tone) {
				scheduleTone(context, tone, baseTime);
			});
			return true;
		}

		async function enable() {
			try {
				await ensureAudioContext();
				enabled = true;
				updateButton(button, enabled);
				return playProfile("READY");
			} catch (error) {
				console.warn("QR display sound could not be enabled", error);
				enabled = false;
				updateButton(button, enabled);
				return false;
			}
		}

		function disable() {
			enabled = false;
			updateButton(button, enabled);
			return false;
		}

		function toggle() {
			return enabled ? disable() : enable();
		}

		async function play(logType) {
			if (!enabled) return false;

			try {
				return playProfile(logType === "OUT" ? "OUT" : "IN");
			} catch (error) {
				console.warn("QR display sound playback failed", error);
				return false;
			}
		}

		return {
			init,
			enable,
			disable,
			toggle,
			play,
			isEnabled,
		};
	}

	global.HRMSQRDisplayAudio = {
		createController,
	};
})(typeof window !== "undefined" ? window : globalThis);
