// 打卡用的手机定位：先要一个够用的位置，太粗再精确定位一次；拿不到时给出原因和对应的做法。
// 与界面、网络解耦：定位对象、时钟、服务端调用都从参数注入，方便测试。

// 200 米的打卡范围用 Wi-Fi 定位就够准，几秒内能拿到；半分钟内刚拿到的位置直接用。
// 总共最多等约 8 秒：精确定位只用第一次剩下的时间，剩得太少就不再尝试
const TOTAL_BUDGET_MS = 8000
const QUICK_FIX = { enableHighAccuracy: false, maximumAge: 30000, timeout: TOTAL_BUDGET_MS }
const PRECISE_FIX_MAX_MS = 5000
const PRECISE_FIX_MIN_MS = 1500
const GOOD_ENOUGH_ACCURACY_M = 100
const ERROR_REASONS = { 1: "denied", 2: "unavailable", 3: "timeout" }
const QR_CHECKIN_METHOD = "hrms.api.qr_attendance.qr_checkin"

const ADVICE = {
	denied: {
		zh: "没有定位权限。请彻底关掉 ERP 应用再打开，询问时点「允许」；如果不再询问，请到 iPhone「设置 › 隐私与安全性 › 定位服务」里允许 Safari 使用定位。连上公司 Wi-Fi 打卡不需要定位。",
		ja: "位置情報の利用が許可されていません。ERPアプリを完全に閉じて開き直し、確認が出たら「許可」を押してください。確認が出ない場合は、iPhoneの「設定 › プライバシーとセキュリティ › 位置情報サービス」でSafariの位置情報を許可してください。社内Wi-Fiにつなげば位置情報なしで打刻できます。",
		en: "Location access is off. Fully close the ERP app, open it again and tap “Allow” when asked. If you are not asked, allow location for Safari in Settings › Privacy & Security › Location Services. On the office Wi-Fi no location is needed.",
	},
	timeout: {
		zh: "暂时拿不到位置。请连上公司 Wi-Fi，或走到窗边再试一次。",
		ja: "現在地を取得できませんでした。社内Wi-Fiにつなぐか、窓の近くでもう一度お試しください。",
		en: "Couldn't get your location. Connect to the office Wi-Fi or move near a window and try again.",
	},
	unsupported: {
		zh: "这台手机无法提供定位。请连上公司 Wi-Fi 再打卡。",
		ja: "この端末では位置情報を利用できません。社内Wi-Fiにつないで打刻してください。",
		en: "This phone can't share its location. Connect to the office Wi-Fi to check in.",
	},
}

const LABELS = {
	locating: { zh: "正在获取位置…", ja: "現在地を取得しています…", en: "Getting your location…" },
	located: { zh: "已获取位置", ja: "現在地を取得しました", en: "Location found" },
	officeNetwork: {
		zh: "已连公司网络，不需要定位",
		ja: "社内ネットワークに接続中のため、位置情報は不要です",
		en: "On the office network — no location needed",
	},
	retry: { zh: "重新获取位置", ja: "もう一度取得", en: "Try Again" },
}

function pick(entry, lang) {
	return entry?.[lang] || entry?.zh || ""
}

export function locationFailureAdvice(reason, lang = "zh") {
	const key = reason === "denied" || reason === "unsupported" ? reason : "timeout"
	return pick(ADVICE[key], lang)
}

export function locationCopy(key, lang = "zh") {
	return pick(LABELS[key], lang)
}

function requestPosition(geolocation, options) {
	return new Promise((resolve) => {
		try {
			geolocation.getCurrentPosition(
				(position) => resolve({ position }),
				(error) => resolve({ error }),
				options
			)
		} catch (_) {
			resolve({ error: { code: 2 } })
		}
	})
}

function toFix(position) {
	const { latitude, longitude, accuracy } = position.coords
	return { latitude, longitude, accuracy: Number.isFinite(accuracy) ? accuracy : Infinity }
}

export async function acquireCheckinLocation({
	geolocation = globalThis.navigator?.geolocation,
	now = () => Date.now(),
} = {}) {
	const startedAt = now()
	const finish = (result) => ({ ...result, elapsedMs: Math.max(0, Math.round(now() - startedAt)) })
	if (!geolocation?.getCurrentPosition) return finish({ ok: false, reason: "unsupported" })

	const quick = await requestPosition(geolocation, QUICK_FIX)
	if (quick.error) return finish({ ok: false, reason: ERROR_REASONS[quick.error.code] || "unavailable" })

	let best = toFix(quick.position)
	const remaining = TOTAL_BUDGET_MS - (now() - startedAt)
	if (best.accuracy > GOOD_ENOUGH_ACCURACY_M && remaining >= PRECISE_FIX_MIN_MS) {
		const precise = await requestPosition(geolocation, {
			enableHighAccuracy: true,
			maximumAge: 0,
			timeout: Math.min(PRECISE_FIX_MAX_MS, Math.round(remaining)),
		})
		if (precise.position) {
			const fix = toFix(precise.position)
			if (fix.accuracy < best.accuracy) best = fix
		}
	}
	return finish({ ok: true, ...best })
}

// 服务端说不需要（连着公司网络）才跳过定位；问不到时照旧定位
export function shouldRequestLocation(requirement) {
	return requirement?.location_required !== false
}

export async function reportLocationFailure(call, { flow, reason, elapsedMs }) {
	try {
		await call("hrms.api.checkin_location.report_location_failure", {
			flow,
			reason,
			elapsed_ms: elapsedMs,
		})
	} catch (_) {
		// 记不上也不影响打卡
	}
}

function coordinates(position) {
	return position ? { latitude: position.latitude, longitude: position.longitude } : {}
}

// 扫码提交：服务端要定位（手机刚从公司 Wi-Fi 换到流量）时，定位后再交一次
export async function submitQrCheckin({ call, token, logType, position = null, locate }) {
	try {
		let message = await call(QR_CHECKIN_METHOD, { token, log_type: logType, ...coordinates(position) })
		if (message?.status === "need_location") {
			const located = await locate()
			if (!located?.ok) {
				return { outcome: "location_failed", reason: located?.reason || "unavailable", location: located }
			}
			message = await call(QR_CHECKIN_METHOD, { token, log_type: logType, ...coordinates(located) })
		}
		if (message?.status === "ok") return { outcome: "success", message }
		return { outcome: "error", message: "" }
	} catch (error) {
		return { outcome: "error", message: error?.message || "" }
	}
}
