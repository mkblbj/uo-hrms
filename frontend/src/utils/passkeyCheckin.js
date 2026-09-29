// 面容/指纹一键打卡的流程逻辑。与界面、网络解耦：依赖都从参数注入，方便测试。

import { locationFailureAdvice } from "./checkinLocation.js"

export const PASSKEY_MODE = "passkey"
export const QR_MODE = "qr"
export const PENDING_OPTIONS_MAX_AGE_MS = 100000
const WIFI_TIP_STORAGE_KEY = "hrms:passkey-wifi-tip-shown"

const COPY = {
	checkInTitle: { zh: "出勤", ja: "出勤", en: "Check In" },
	checkOutTitle: { zh: "退勤", ja: "退勤", en: "Check Out" },
	passkeyHint: { zh: "看一眼手机即可打卡", ja: "顔認証・指紋で打刻", en: "Face ID or fingerprint" },
	verifying: { zh: "确认中…", ja: "確認中…", en: "Checking…" },
	firstTimeTitle: { zh: "以后打卡看一眼就行", ja: "次回から顔認証だけで打刻", en: "Check in with just a glance" },
	firstTimeBody: {
		zh: "在这台手机上设置一次面容/指纹，以后不用再扫码。手机会弹两次确认。",
		ja: "この端末で顔認証・指紋を一度設定すると、QRコードは不要になります。確認が2回表示されます。",
		en: "Set up Face ID or fingerprint once on this phone and you won't need the QR code again. Your phone will ask you to confirm twice.",
	},
	start: { zh: "开始", ja: "はじめる", en: "Get Started" },
	scanThisTime: { zh: "这次先扫码", ja: "今回はQRコードで", en: "Scan the QR Code This Time" },
	fallbackTitle: { zh: "这次没能验证", ja: "認証できませんでした", en: "Couldn't verify this time" },
	fallbackBody: {
		zh: "可以再试一次；换了新手机的话，在这台手机上重新设置。",
		ja: "もう一度お試しください。機種変更した場合は、この端末で設定し直してください。",
		en: "Try again. If you changed phones, set up this phone again.",
	},
	retry: { zh: "再试一次", ja: "もう一度", en: "Try Again" },
	resetup: { zh: "在这台手机上重新设置", ja: "この端末で設定し直す", en: "Set Up This Phone Again" },
	presenceTitle: {
		zh: "没能确认你在公司",
		ja: "社内にいることを確認できませんでした",
		en: "Couldn't confirm you're at the office",
	},
	presenceBodyAt: {
		zh: "请到「{0}」扫码打卡。",
		ja: "「{0}」のQRコードで打刻してください。",
		en: "Please scan the QR code at {0}.",
	},
	presenceBody: {
		zh: "请到门口扫码打卡。",
		ja: "入口のQRコードで打刻してください。",
		en: "Please scan the QR code at the entrance.",
	},
	locationFailedBody: {
		zh: "没能获取定位。请在手机设置里允许定位，或者这次扫码打卡。",
		ja: "位置情報を取得できませんでした。位置情報を許可するか、今回はQRコードで打刻してください。",
		en: "We couldn't get your location. Allow location access, or scan the QR code this time.",
	},
	scanQr: { zh: "扫码打卡", ja: "QRコードで打刻", en: "Scan QR Code" },
	wifiTip: {
		zh: "连上公司 Wi-Fi，下次连定位都不用问",
		ja: "社内Wi-Fiにつなぐと、次回から位置情報の確認が不要になります",
		en: "Connect to the office Wi-Fi and you won't be asked for your location next time",
	},
	checkinFailed: {
		zh: "打卡没有成功，请再试一次",
		ja: "打刻できませんでした。もう一度お試しください",
		en: "Check-in failed. Please try again.",
	},
}

export function pickPasskeyCopy(key, lang = "zh", ...args) {
	const entry = COPY[key] || {}
	const text = entry[lang] || entry.zh || ""
	return args.reduce((result, value, index) => result.replace(`{${index}}`, value), text)
}

export function resolveCheckinMode({ context, platformSupported }) {
	return context?.enabled && platformSupported ? PASSKEY_MODE : QR_MODE
}

export function needsLocation(context) {
	return !context?.on_office_network
}

export function classifyWebAuthnError(error) {
	const name = error?.name || ""
	if (name === "InvalidStateError") return "already_registered"
	if (name === "NotAllowedError" || name === "AbortError") return "cancelled"
	return "failed"
}

export function shouldShowWifiTip(evidence, storage) {
	if (evidence !== "gps" || !storage) return false
	try {
		if (storage.getItem(WIFI_TIP_STORAGE_KEY)) return false
		storage.setItem(WIFI_TIP_STORAGE_KEY, "1")
		return true
	} catch (_) {
		return false
	}
}

export function getSheetContent(
	variant,
	lang = "zh",
	{ locationLabel = "", locationFailed = false, locationFailureReason = null, message = "" } = {}
) {
	const t = (key, ...args) => pickPasskeyCopy(key, lang, ...args)
	if (variant === "error") {
		return {
			icon: "lucide-scan-face",
			title: t("checkinFailed"),
			body: message || t("fallbackBody"),
			actions: [
				{ id: "retry", label: t("retry"), primary: true },
				{ id: "resetup", label: t("resetup"), primary: false },
				{ id: "scan", label: t("scanThisTime"), primary: false },
			],
		}
	}
	if (variant === "first_time") {
		return {
			icon: "lucide-scan-face",
			title: t("firstTimeTitle"),
			body: t("firstTimeBody"),
			actions: [
				{ id: "start", label: t("start"), primary: true },
				{ id: "scan", label: t("scanThisTime"), primary: false },
			],
		}
	}
	if (variant === "fallback") {
		return {
			icon: "lucide-scan-face",
			title: t("fallbackTitle"),
			body: t("fallbackBody"),
			actions: [
				{ id: "retry", label: t("retry"), primary: true },
				{ id: "resetup", label: t("resetup"), primary: false },
				{ id: "scan", label: t("scanThisTime"), primary: false },
			],
		}
	}
	let body = t("presenceBody")
	if (locationFailed) {
		body = locationFailureReason ? locationFailureAdvice(locationFailureReason, lang) : t("locationFailedBody")
	}
	else if (locationLabel) body = t("presenceBodyAt", locationLabel)
	return {
		icon: "lucide-map-pin",
		title: t("presenceTitle"),
		body,
		actions: [{ id: "scan", label: t("scanQr"), primary: true }],
	}
}

export function extractFrappeError(data) {
	if (data?._server_messages) {
		try {
			const messages = JSON.parse(data._server_messages)
			if (messages?.length) {
				const parsed = JSON.parse(messages[0])
				if (parsed?.message) return String(parsed.message).replace(/<[^>]*>/g, "")
			}
		} catch (_) {
			// 解析失败时继续尝试 exception
		}
	}
	const match = String(data?.exception || "").match(/frappe\.exceptions\.\w+:\s*(.+)/)
	return match ? match[1].trim() : ""
}

export function createFrappeCaller({ fetchImpl, getCsrfToken }) {
	return async function call(method, params = {}) {
		const response = await fetchImpl(`/api/method/${method}`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": getCsrfToken() || "",
			},
			body: JSON.stringify(params),
		})
		let data = {}
		try {
			data = await response.json()
		} catch (_) {
			data = {}
		}
		if (!response.ok || data.exc || data.exception) {
			throw new Error(extractFrappeError(data))
		}
		return data.message
	}
}

function positionParams(position) {
	if (!position) return {}
	return { latitude: position.latitude, longitude: position.longitude, accuracy: position.accuracy }
}

async function registerThisDevice(deps) {
	const options = await deps.call("hrms.api.passkey.register_options", {})
	let credential
	try {
		credential = await deps.startRegistration({ optionsJSON: options })
	} catch (error) {
		const kind = classifyWebAuthnError(error)
		if (kind === "already_registered") return { outcome: "registered" }
		return { outcome: "setup_failed", kind }
	}
	await deps.call("hrms.api.passkey.register_complete", {
		credential: JSON.stringify(credential),
		device_name: deps.deviceName(),
	})
	return { outcome: "registered" }
}

async function beginWithPresence({ logType, context, deps }) {
	let position = null
	if (needsLocation(context)) {
		try {
			position = await deps.getPosition()
		} catch (error) {
			return { failed: { outcome: "location_failed", reason: error?.reason || null } }
		}
	}
	let begin = await deps.call("hrms.api.passkey.begin_checkin", { log_type: logType, ...positionParams(position) })
	if (begin?.status === "need_location" && !position) {
		try {
			position = await deps.getPosition()
		} catch (error) {
			return { failed: { outcome: "location_failed", reason: error?.reason || null } }
		}
		begin = await deps.call("hrms.api.passkey.begin_checkin", { log_type: logType, ...positionParams(position) })
	}
	return { begin }
}

export async function runPasskeyCheckin({ logType, context, deps, setup = false, pending = null }) {
	try {
		let setupDone = false
		if (setup || !context?.has_passkey) {
			const registered = await registerThisDevice(deps)
			if (registered.outcome !== "registered") return registered
			setupDone = true
		}

		const freshPending =
			pending?.options && deps.now() - (pending.createdAt || 0) < PENDING_OPTIONS_MAX_AGE_MS ? pending : null
		let options = freshPending?.options || null
		let evidence = freshPending?.evidence || null

		while (!options) {
			const { begin, failed } = await beginWithPresence({ logType, context, deps })
			if (failed) return failed
			const status = begin?.status
			if (status === "ok") {
				options = begin.options
				evidence = begin.evidence
			} else if (status === "no_passkey" && !setupDone) {
				const registered = await registerThisDevice(deps)
				if (registered.outcome !== "registered") return registered
				setupDone = true
			} else if (status === "presence_unconfirmed" || status === "need_location") {
				return { outcome: "presence_unconfirmed", reason: begin.reason || null }
			} else if (status === "disabled") {
				return { outcome: "disabled" }
			} else {
				return { outcome: "error", message: "" }
			}
		}

		let credential
		try {
			credential = await deps.startAuthentication({ optionsJSON: options })
		} catch (error) {
			return {
				outcome: "webauthn_failed",
				kind: classifyWebAuthnError(error),
				pending: { options, evidence, createdAt: freshPending?.createdAt ?? deps.now() },
			}
		}

		const message = await deps.call("hrms.api.passkey.complete_checkin", { credential: JSON.stringify(credential) })
		return { outcome: "success", message, evidence: message?.evidence || evidence }
	} catch (error) {
		return { outcome: "error", message: error?.message || "" }
	}
}
