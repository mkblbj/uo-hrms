export const isChrome = () =>
	navigator.userAgent.toLowerCase().includes("chrome")

export function resolvePushPromptState({
	isIos = false,
	isStandalone = false,
	permission = "default",
	hasToken = false,
	supported = false,
} = {}) {
	if (isIos && !isStandalone) return "install"
	if (!supported) return "hidden"
	if (permission === "denied") return "denied"
	if (permission === "granted" && hasToken) return "enabled"
	return "prompt"
}

export const showNotification = (payload) => {
	const registration = window.frappePushNotification.serviceWorkerRegistration
	if (!registration) return

	const notificationTitle = payload?.data?.title
	const notificationOptions = {
		body: payload?.data?.body || "",
	}
	if (payload?.data?.notification_icon) {
		notificationOptions["icon"] = payload.data.notification_icon
	}
	if (isChrome()) {
		notificationOptions["data"] = {
			url: payload?.data?.click_action,
		}
	} else {
		if (payload?.data?.click_action) {
			notificationOptions["actions"] = [
				{
					action: payload.data.click_action,
					title: "View Details",
				},
			]
		}
	}

	registration.showNotification(notificationTitle, notificationOptions)
}
