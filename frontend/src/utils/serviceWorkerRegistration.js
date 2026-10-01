export function waitForActiveServiceWorker(registration) {
	if (!registration) {
		return Promise.reject(new Error("Service worker registration is unavailable"))
	}
	if (registration.active) return Promise.resolve(registration)

	return new Promise((resolve, reject) => {
		let worker = null
		const timer = setTimeout(() => {
			finish(new Error("Service worker did not activate"))
		}, 30000)

		function finish(error) {
			clearTimeout(timer)
			registration.removeEventListener?.("updatefound", check)
			worker?.removeEventListener("statechange", check)
			if (error) reject(error)
			else resolve(registration)
		}

		function check() {
			if (registration.active) return finish()
			const current = registration.installing || registration.waiting
			if (current !== worker) {
				worker?.removeEventListener("statechange", check)
				worker = current
				worker?.addEventListener("statechange", check)
			}
			if (worker?.state === "redundant") {
				finish(new Error("Service worker installation failed"))
			}
		}

		registration.addEventListener?.("updatefound", check)
		check()
	})
}

export async function getTokenWithServiceWorker({ registration, register, getToken }) {
	await waitForActiveServiceWorker(registration)
	try {
		return { token: await getToken(registration), registration }
	} catch (error) {
		if (
			error?.name !== "InvalidStateError" ||
			!error.message?.includes("Getting push subscription requires a service worker")
		) {
			throw error
		}
	}

	try {
		await registration.unregister?.()
	} catch {
		// Register a fresh worker even if the stale registration cannot be removed.
	}
	const freshRegistration = await register()
	await waitForActiveServiceWorker(freshRegistration)
	return { token: await getToken(freshRegistration), registration: freshRegistration }
}
