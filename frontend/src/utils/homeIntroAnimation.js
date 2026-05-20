export const INTRO_KEY = "hrms_home_intro_played"

export function shouldPlayIntro({ storage, matchMedia } = {}) {
	if (!storage) return false
	try {
		if (storage.getItem(INTRO_KEY)) return false
	} catch (_) {
		return false
	}
	try {
		if (typeof matchMedia !== "function") {
			// matchMedia unavailable — assume motion allowed
		} else {
			const mq = matchMedia("(prefers-reduced-motion: reduce)")
			if (mq && mq.matches) return false
		}
	} catch (_) {
		// 忽略 matchMedia 异常，按"动效允许"继续
	}
	return true
}

export function markIntroPlayed({ storage } = {}) {
	if (!storage) return
	try {
		storage.setItem(INTRO_KEY, "1")
	} catch (_) {
		// 忽略 storage 写入异常（隐私模式等）
	}
}
