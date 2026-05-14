/* global __HRMS_FRONTEND_VERSION__, __HRMS_FRONTEND_BUILD_TIME__ */

export const FRONTEND_VERSION_PATH = "/assets/hrms/frontend/frontend-version.json"
export const FRONTEND_VERSION_CHECK_INTERVAL_MS = 15 * 60 * 1000

function readDefinedVersion() {
	return typeof __HRMS_FRONTEND_VERSION__ === "string" ? __HRMS_FRONTEND_VERSION__ : "dev"
}

function readDefinedBuildTime() {
	return typeof __HRMS_FRONTEND_BUILD_TIME__ === "string" ? __HRMS_FRONTEND_BUILD_TIME__ : ""
}

export function getCurrentFrontendVersion() {
	return {
		version: readDefinedVersion(),
		buildTime: readDefinedBuildTime(),
	}
}

function getVersionUrl(path = FRONTEND_VERSION_PATH, now = Date.now) {
	return `${path}?t=${now()}`
}

export async function fetchFrontendVersion({
	fetchImpl = globalThis.fetch,
	path = FRONTEND_VERSION_PATH,
	now = Date.now,
} = {}) {
	if (typeof fetchImpl !== "function") return null

	try {
		const response = await fetchImpl(getVersionUrl(path, now), {
			cache: "no-store",
			credentials: "same-origin",
		})
		if (!response?.ok) return null

		const data = await response.json()
		if (!data?.version) return null

		return {
			version: data.version,
			buildTime: data.buildTime || "",
		}
	} catch {
		return null
	}
}

export function hasNewFrontendVersion({ currentVersion, remoteVersion } = {}) {
	return Boolean(
		currentVersion?.version &&
			remoteVersion?.version &&
			currentVersion.version !== remoteVersion.version
	)
}

export function createFrontendVersionChecker({
	currentVersion = getCurrentFrontendVersion(),
	fetchVersion = fetchFrontendVersion,
} = {}) {
	return {
		async check() {
			try {
				const remoteVersion = await fetchVersion()
				return {
					currentVersion,
					remoteVersion,
					updateAvailable: hasNewFrontendVersion({ currentVersion, remoteVersion }),
				}
			} catch {
				return {
					currentVersion,
					remoteVersion: null,
					updateAvailable: false,
				}
			}
		},
	}
}

function getStoredServiceWorkerRegistration() {
	return globalThis.window?.frappePushNotification?.serviceWorkerRegistration || null
}

export async function requestServiceWorkerUpdate({
	serviceWorkerRegistration = getStoredServiceWorkerRegistration(),
	serviceWorker = globalThis.navigator?.serviceWorker,
} = {}) {
	try {
		const registration =
			serviceWorkerRegistration ||
			(typeof serviceWorker?.getRegistration === "function"
				? await serviceWorker.getRegistration()
				: null)

		if (typeof registration?.update !== "function") return false

		await registration.update()
		return true
	} catch {
		return false
	}
}
