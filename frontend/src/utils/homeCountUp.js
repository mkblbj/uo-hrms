export function easeOutCubic(t) {
	if (t <= 0) return 0
	if (t >= 1) return 1
	return 1 - Math.pow(1 - t, 3)
}

export function interpolateCountUp(from, to, progress) {
	const eased = easeOutCubic(progress)
	return from + (to - from) * eased
}

export function formatCountUp(value, decimals = 0) {
	if (!Number.isFinite(value)) return decimals > 0 ? (0).toFixed(decimals) : "0"
	if (decimals > 0) return value.toFixed(decimals)
	return String(Math.round(value))
}

const DEFAULT_DURATION = 900

/**
 * Drive a numeric ref from 0 to target with ease-out cubic.
 * Returns a cancel function. Caller is responsible for setting the displayed
 * value when not animating (e.g. when reduced-motion is preferred or after
 * the animation has already run once).
 */
export function runCountUp({
	target,
	duration = DEFAULT_DURATION,
	onUpdate,
	now = () => performance.now(),
	schedule = (cb) => requestAnimationFrame(cb),
} = {}) {
	if (typeof onUpdate !== "function") return () => {}
	if (!Number.isFinite(target)) {
		onUpdate(0)
		return () => {}
	}
	const start = now()
	let cancelled = false

	const step = () => {
		if (cancelled) return
		const elapsed = now() - start
		const progress = duration > 0 ? Math.min(elapsed / duration, 1) : 1
		onUpdate(interpolateCountUp(0, target, progress))
		if (progress < 1) schedule(step)
	}

	schedule(step)
	return () => {
		cancelled = true
	}
}
