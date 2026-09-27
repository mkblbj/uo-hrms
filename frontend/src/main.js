import { createApp } from "vue"
import App from "./App.vue"
import router from "./router"
import { initSocket } from "./socket"

import {
	Button,
	setConfig,
	frappeRequest,
	resourcesPlugin,
	FormControl,
} from "frappe-ui"
import { translationsPlugin } from "./plugins/translationsPlugin.js"
import EmptyState from "@/components/EmptyState.vue"
import { initializeBootLanguage } from "@/utils/language"

import { IonicVue } from "@ionic/vue"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { employeeResource } from "@/data/employee"

import dayjs from "@/utils/dayjs"
import getIonicConfig from "@/utils/ionicConfig"

import FrappePushNotification from "../public/frappe-push-notification"

/* Core CSS required for Ionic components to work properly */
import "@ionic/vue/css/core.css"

/* Theme variables */
import "./theme/variables.css"

import "./main.css"

const app = createApp(App)
const socket = initSocket()

setConfig("resourceFetcher", frappeRequest)
app.use(resourcesPlugin)
app.use(translationsPlugin)

app.component("Button", Button)
app.component("FormControl", FormControl)
app.component("EmptyState", EmptyState)

app.use(router)
app.use(IonicVue, getIonicConfig())

if (session?.isLoggedIn && !employeeResource?.data) {
	employeeResource.reload()
}

app.provide("$session", session)
app.provide("$user", userResource)
app.provide("$employee", employeeResource)
app.provide("$socket", socket)
app.provide("$dayjs", dayjs)

const registerServiceWorker = () => {
	const push = new FrappePushNotification("hrms")
	window.frappePushNotification = push
	push.ready = (async () => {
		if (!("serviceWorker" in navigator)) {
			throw new Error("Service worker not enabled/supported by the browser")
		}

		let serviceWorkerURL = "/hrms-sw.js"
		let config = null
		let configError = null
		if (window.frappe?.boot?.push_relay_server_url) {
			try {
				config = await push.fetchWebConfig()
				serviceWorkerURL = `${serviceWorkerURL}?config=${encodeURIComponent(
					JSON.stringify(config)
				)}`
			} catch (error) {
				configError = error
			}
		}

		push.serviceWorkerURL = serviceWorkerURL
		push.serviceWorkerOptions = {
			type: "classic",
			scope: "/hrms",
			updateViaCache: "none",
		}
		const registration = await navigator.serviceWorker.register(serviceWorkerURL, {
			...push.serviceWorkerOptions,
		})
		push.serviceWorkerRegistration = registration
		if (configError) throw configError
		if (config) await push.initialize(registration)
	})()
	push.ready.catch((error) => {
		console.error("Failed to initialize push service worker", error)
	})
}

router.isReady().then(async () => {
	if (import.meta.env.DEV) {
		await frappeRequest({
			url: "/api/method/hrms.www.hrms.get_context_for_dev",
		}).then(async (values) => {
			if (!window.frappe) window.frappe = {}
			window.frappe.boot = values
		})
	}

	initializeBootLanguage()
	await translationsPlugin.isReady()
	registerServiceWorker()
	app.mount("#app")
})

router.beforeEach(async (to, _, next) => {
	let isLoggedIn = session.isLoggedIn

	try {
		if (isLoggedIn) await userResource.reload()
	} catch (error) {
		isLoggedIn = false
	}

	if (!isLoggedIn) {
		// password reset page is outside the PWA scope
		if (to.path === "/update-password") {
			return next(false)
		} else if (!["Login", "ForgotPassword"].includes(to.name)) {
			return next({ name: "Login" })
		}
	}

	if (isLoggedIn && to.name !== "InvalidEmployee") {
		await employeeResource.promise
		// user should be an employee to access the app
		// since all views are employee specific
		if (
			!employeeResource?.data ||
			employeeResource?.data?.user_id !== userResource.data.name
		) {
			next({ name: "InvalidEmployee" })
		} else if (["Login", "ForgotPassword"].includes(to.name)) {
			next({ name: "Home" })
		} else {
			next()
		}
	} else {
		next()
	}
})
