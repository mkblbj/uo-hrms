<template>
	<div class="checkin-panel" :class="{ 'intro-play': introPlay }">
		<PushNotificationPrompt />

		<section
			v-if="todaySaleEvent"
			class="home-sale-banner intro-stagger intro-stagger-0"
			:style="saleBannerStyle(todaySaleEvent)"
		>
			<span class="home-sale-dot"></span>
			<div class="home-sale-copy">
				<strong>{{ tSale("title") }}</strong>
				<span>{{ todaySaleEvent.title }}・{{ tSale("hint") }}</span>
			</div>
		</section>

		<RosterPreferenceBanner :notice="homePreferenceNotice" :labels="preferenceLabels" />

		<HomeHeroCard
			ref="heroCardRef"
			class="intro-stagger intro-stagger-1"
			:employee-name="employee?.data?.first_name || employee?.data?.employee_name || ''"
			:greeting="getGreeting()"
			:date-label="formatDate()"
			:weather-text="weatherSummary"
			:work-status="props.workStatus?.data"
			:stats="dashboardStats.data"
			:stats-loading="dashboardStats.loading"
			:lang="currentLanguage"
			:intro-play="introPlay"
		/>

		<HomeSummaryCard class="intro-stagger intro-stagger-2" :lang="currentLanguage" />
		<HomeStatsGrid
			class="intro-stagger intro-stagger-3"
			:stats="dashboardStats.data"
			:lang="currentLanguage"
		/>
	</div>

	<HomeScanActionBar
		:cta="primaryScanMeta"
		:work-status="props.workStatus?.data"
		:lang="currentLanguage"
		:mode="checkinMode"
		:busy="passkeyBusy"
		:disabled="!isMobileCheckinAllowed || props.workStatus?.loading"
		@scan="onPrimaryAction"
	/>

	<PasskeyCheckinSheet
		:is-open="passkeySheet.isOpen"
		:variant="passkeySheet.variant"
		:lang="currentLanguage"
		:location-label="passkeyContext.data?.location?.description || ''"
		:location-failed="passkeySheet.locationFailed"
		:location-failure-reason="passkeySheet.locationFailureReason"
		:message="passkeySheet.message"
		@action="onPasskeySheetAction"
		@dismiss="passkeySheet.isOpen = false"
	/>

	<!-- 扫码模态框 -->
	<QRScannerModal
		v-if="primaryScanMeta"
		ref="qrScannerRef"
		:is-open="showQRScanner"
		:log-type="primaryScanMeta.action"
		@close="showQRScanner = false"
		@success="handleQRScanSuccess"
	/>

	<CheckinSuccessOverlay
		v-if="successOverlayState.model"
		:is-open="successOverlayState.isOpen"
		:actions-visible="successOverlayState.actionsVisible"
		:model="successOverlayState.model"
		@primary="handleSuccessPrimary"
		@close="handleSuccessOverlayDismiss"
	/>
</template>

<script>
const defaultSchedule = (callback, delay) =>
	(globalThis.window || globalThis).setTimeout(callback, delay)
const defaultCancel = (timerId) => (globalThis.window || globalThis).clearTimeout(timerId)

function hasActiveSuccessOverlay(state) {
	return Boolean(state.isOpen || state.actionsVisible || state.model || state.returnRoute)
}

export function createSuccessOverlayController({
	state = {
		isOpen: false,
		actionsVisible: false,
		model: null,
		returnRoute: null,
	},
	schedule = defaultSchedule,
	cancel = defaultCancel,
} = {}) {
	let successActionsTimer = null

	function clearActionsTimer() {
		if (successActionsTimer !== null) {
			cancel(successActionsTimer)
			successActionsTimer = null
		}
	}

	function resetState() {
		state.isOpen = false
		state.actionsVisible = false
		state.model = null
		state.returnRoute = null
	}

	function open(model, currentRoute) {
		state.returnRoute = currentRoute
		state.model = model
		state.actionsVisible = false
		state.isOpen = true
		clearActionsTimer()
		successActionsTimer = schedule(() => {
			state.actionsVisible = true
		}, model.delayMs)
	}

	function close({ currentRoute = null, replaceRoute } = {}) {
		const previousRoute = state.returnRoute
		clearActionsTimer()
		resetState()
		if (
			previousRoute &&
			currentRoute &&
			currentRoute !== previousRoute &&
			typeof replaceRoute === "function"
		) {
			replaceRoute(previousRoute)
		}
	}

	function primary(pushRoute) {
		const targetRoute = state.model?.primaryRoute
		clearActionsTimer()
		resetState()
		if (targetRoute && typeof pushRoute === "function") {
			pushRoute(targetRoute)
		}
	}

	function didDismiss(_event, options = {}) {
		if (!hasActiveSuccessOverlay(state)) {
			return false
		}

		close(options)
		return true
	}

	function dispose() {
		clearActionsTimer()
	}

	return {
		open,
		close,
		primary,
		didDismiss,
		dispose,
	}
}
</script>

<script setup>
import { createResource, toast } from "frappe-ui"
import { onIonViewWillEnter } from "@ionic/vue"
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import CheckinSuccessOverlay from "@/components/home/CheckinSuccessOverlay.vue"
import HomeHeroCard from "@/components/home/HomeHeroCard.vue"
import PushNotificationPrompt from "@/components/home/PushNotificationPrompt.vue"
import HomeScanActionBar from "@/components/home/HomeScanActionBar.vue"
import HomeStatsGrid from "@/components/home/HomeStatsGrid.vue"
import PasskeyCheckinSheet from "@/components/home/PasskeyCheckinSheet.vue"
import QRScannerModal from "@/components/QRScannerModal.vue"
import HomeSummaryCard from "@/components/work_roster/HomeSummaryCard.vue"
import RosterPreferenceBanner from "@/components/work_roster/RosterPreferenceBanner.vue"
import { settings } from "@/data/settings"
import {
	acquireCheckinLocation,
	locationFailureAdvice,
	reportLocationFailure,
	submitQrCheckin,
} from "@/utils/checkinLocation"
import { formatTimestamp } from "@/utils/formatters"
import {
	buildSuccessOverlayModel,
	emitCheckinStatusChanged,
	getHeroCardMeta,
	resolveHomeLanguage,
} from "@/utils/homeExperience"
import { shouldPlayIntro, markIntroPlayed } from "@/utils/homeIntroAnimation"
import {
	PASSKEY_MODE,
	createFrappeCaller,
	pickPasskeyCopy,
	resolveCheckinMode,
	runPasskeyCheckin,
	shouldShowWifiTip,
} from "@/utils/passkeyCheckin"
import {
	formatRosterPreferenceTitle,
	getRosterCopy,
	resolveHomePreferenceNotice,
} from "@/utils/rosterCalendar"

const props = defineProps({
	workStatus: {
		type: Object,
		required: true,
	},
})

const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const route = useRoute()
const router = useRouter()
const showQRScanner = ref(false)
const qrScannerRef = ref(null)
const heroCardRef = ref(null)
const introPlay = ref(false)
const currentLanguage = resolveHomeLanguage(window.frappe?.boot)
const PREFERENCE_LABEL_KEYS = ["submitPreference", "editPreference", "submitted", "deadline"]
const preferenceLabels = Object.fromEntries(
	PREFERENCE_LABEL_KEYS.map((key) => [key, getRosterCopy(key, currentLanguage)])
)
const successOverlayState = reactive({
	isOpen: false,
	actionsVisible: false,
	model: null,
	returnRoute: null,
})
const successOverlayController = createSuccessOverlayController({
	state: successOverlayState,
})

const dashboardStats = createResource({
	url: "hrms.api.get_employee_dashboard_stats",
	auto: true,
})

const weather = createResource({
	url: "hrms.api.get_weather_data",
	auto: true,
	cache: ["weather_data", 10 * 60 * 1000],
})

const homeScheduleSummary = createResource({
	url: "work_roster.api.schedule.get_home_schedule_summary",
	auto: false,
	cache: false,
})

const isMobileCheckinAllowed = computed(() =>
	Boolean(settings.data?.allow_employee_checkin_from_mobile_app)
)
const heroCardMeta = computed(() =>
	getHeroCardMeta({
		workStatus: props.workStatus?.data,
		lang: currentLanguage,
		formatLastCheckin: formatTimestamp,
		translate: __,
		allowPrimaryScan: isMobileCheckinAllowed.value,
	})
)
const primaryScanMeta = computed(() => heroCardMeta.value.cta)
const weatherSummary = computed(() => {
	if (!weather.data) return ""
	const icon = weather.data?.condition?.text ? "⛅" : ""
	const temp = Math.round(weather.data.temp_c)
	return `${icon} ${temp}°`.trim()
})
const todaySaleEvent = computed(() => homeScheduleSummary.data?.today_event || null)
const homePreferenceNotice = computed(() => {
	const notice = resolveHomePreferenceNotice(homeScheduleSummary.data?.preference_notice)
	if (!notice) return null
	return {
		...notice,
		title: formatRosterPreferenceTitle(notice, currentLanguage),
	}
})

const openQRScanner = () => {
	if (
		props.workStatus?.loading ||
		!settings.data?.allow_employee_checkin_from_mobile_app ||
		!primaryScanMeta.value
	) {
		return
	}
	showQRScanner.value = true
}

function loadHomeScheduleSummary() {
	homeScheduleSummary.fetch()
}

const passkeyContext = createResource({
	url: "hrms.api.passkey.get_checkin_context",
	auto: true,
})
const platformSupported = ref(false)
const passkeyBusy = ref(false)
const passkeySheet = reactive({
	isOpen: false,
	variant: "first_time",
	locationFailed: false,
	locationFailureReason: null,
	message: "",
	pending: null,
})
const checkinMode = computed(() =>
	resolveCheckinMode({ context: passkeyContext.data, platformSupported: platformSupported.value })
)
const callFrappe = createFrappeCaller({
	fetchImpl: (...args) => fetch(...args),
	getCsrfToken: () => window.csrf_token || "",
})

async function detectPlatformSupport() {
	try {
		platformSupported.value = Boolean(
			window.PublicKeyCredential &&
				(await window.PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable())
		)
	} catch (_) {
		platformSupported.value = false
	}
}

// 面容打卡要定位时用：拿不到就记下原因，交给面板说明
async function getCheckinPosition() {
	const located = await acquireCheckinLocation()
	if (!located.ok) {
		reportLocationFailure(callFrappe, {
			flow: "passkey",
			reason: located.reason,
			elapsedMs: located.elapsedMs,
		})
		throw Object.assign(new Error(located.reason), { reason: located.reason })
	}
	return located
}

function deviceName() {
	const ua = navigator.userAgent || ""
	if (/iPhone/.test(ua)) return "iPhone"
	if (/iPad/.test(ua)) return "iPad"
	if (/Android/.test(ua)) return "Android"
	return "Browser"
}

function openPasskeySheet(variant, extra = {}) {
	Object.assign(
		passkeySheet,
		{
			isOpen: true,
			variant,
			locationFailed: false,
			locationFailureReason: null,
			message: "",
			pending: null,
		},
		extra
	)
}

function onPrimaryAction() {
	if (checkinMode.value !== PASSKEY_MODE) {
		openQRScanner()
		return
	}
	if (!passkeyContext.data?.has_passkey) {
		openPasskeySheet("first_time")
		return
	}
	startPasskeyCheckin()
}

async function onPasskeySheetAction(actionId) {
	const pending = passkeySheet.pending
	passkeySheet.isOpen = false
	if (actionId === "scan") {
		openQRScanner()
		return
	}
	await startPasskeyCheckin({
		setup: actionId === "start" || actionId === "resetup",
		pending: actionId === "retry" ? pending : null,
	})
}

async function startPasskeyCheckin({ setup = false, pending = null } = {}) {
	const action = primaryScanMeta.value?.action
	if (!action || passkeyBusy.value) return
	passkeyBusy.value = true
	try {
		const { startAuthentication, startRegistration } = await import("@simplewebauthn/browser")
		const result = await runPasskeyCheckin({
			logType: action,
			context: passkeyContext.data,
			setup,
			pending,
			deps: {
				call: callFrappe,
				startRegistration,
				startAuthentication,
				getPosition: getCheckinPosition,
				deviceName,
				now: () => Date.now(),
			},
		})
		// 本机刚设置好但这次没打成：先刷新状态，「再试一次」就不会重新设置
		if (result.setupDone && result.outcome !== "success") {
			try {
				await passkeyContext.reload()
			} catch (_) {
				// 刷新失败也照常给出结果面板
			}
		}
		await handlePasskeyOutcome(action, result)
	} finally {
		passkeyBusy.value = false
	}
}

async function handlePasskeyOutcome(action, result) {
	if (result.outcome === "success") {
		passkeyContext.reload()
		await handleCheckinSuccess(action, result.message)
		if (shouldShowWifiTip(result.evidence, safeLocalStorage())) {
			toast.info(pickPasskeyCopy("wifiTip", currentLanguage))
		}
		return
	}
	if (result.outcome === "location_failed") {
		openPasskeySheet("presence", { locationFailed: true, locationFailureReason: result.reason || null })
		return
	}
	if (result.outcome === "presence_unconfirmed") {
		openPasskeySheet("presence")
		return
	}
	if (result.outcome === "webauthn_failed" || result.outcome === "setup_failed") {
		openPasskeySheet("fallback", { pending: result.pending || null })
		return
	}
	if (result.outcome === "disabled") {
		passkeyContext.reload()
		openQRScanner()
		return
	}
	// 服务端报错（冷却规则、核对失败、超时等）：给出原因，并留着重试、重新设置和扫码
	openPasskeySheet("error", { message: result.message || "" })
}

function safeLocalStorage() {
	try {
		return window.localStorage
	} catch (_) {
		return null
	}
}

function tSale(key) {
	const labels = {
		title: {
			zh: "今日大促",
			ja: "本日セール",
			en: "Sale Today",
		},
		hint: {
			zh: "订单量预计增加",
			ja: "注文増加見込み",
			en: "Higher order volume expected",
		},
	}
	return labels[key]?.[currentLanguage] || labels[key]?.zh || key
}

function saleBannerStyle(event) {
	const color = event.color || "#F59E0B"
	const background = tintColor(color, 0.84)
	return {
		backgroundColor: background,
		borderColor: color,
		color: readableTextColor(background),
	}
}

function readableTextColor(color) {
	const rgb = hexToRgb(color)
	if (!rgb) return "#111827"
	const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000
	return brightness < 150 ? "#ffffff" : "#111827"
}

function tintColor(color, whiteMix) {
	const rgb = hexToRgb(color)
	if (!rgb) return color
	const mix = Math.max(0, Math.min(1, whiteMix))
	const r = Math.round(rgb.r + (255 - rgb.r) * mix)
	const g = Math.round(rgb.g + (255 - rgb.g) * mix)
	const b = Math.round(rgb.b + (255 - rgb.b) * mix)
	return `rgb(${r}, ${g}, ${b})`
}

function hexToRgb(color) {
	const match = String(color || "")
		.trim()
		.match(/^#?([0-9a-f]{6})$/i)
	if (!match) return null
	const intValue = parseInt(match[1], 16)
	return {
		r: (intValue >> 16) & 255,
		g: (intValue >> 8) & 255,
		b: intValue & 255,
	}
}

function openSuccessOverlay(model) {
	successOverlayController.open(model, route.fullPath)
}

function closeSuccessOverlay() {
	successOverlayController.close({
		currentRoute: route.fullPath,
		replaceRoute: (target) => router.replace(target),
	})
}

function handleSuccessPrimary() {
	successOverlayController.primary((target) => router.push(target))
}

function handleSuccessOverlayDismiss(event) {
	successOverlayController.didDismiss(event, {
		currentRoute: route.fullPath,
		replaceRoute: (target) => router.replace(target),
	})
}

async function handleCheckinSuccess(action, responseMessage) {
	try {
		await dashboardStats.reload()
	} catch (reloadError) {
		console.error("Failed to refresh dashboard stats", reloadError)
	}
	try {
		await heroCardRef.value?.reloadAttendance?.()
	} catch (reloadError) {
		console.error("Failed to refresh attendance heatmap", reloadError)
	}

	// 发送全局事件通知工作状态徽章更新
	emitCheckinStatusChanged(window, { log_type: action })
	showQRScanner.value = false
	// iOS PWA: 等上一个 ion-modal 开始 dismiss 后再开启 success overlay，
	// 避免两个 ion-modal 的进出场动画重叠导致子 CSS 动画被 WebKit 合成器冻结。
	await new Promise((resolve) => setTimeout(resolve, 320))
	openSuccessOverlay(
		buildSuccessOverlayModel({
			action,
			lang: currentLanguage,
			responseMessage,
			monthHours: dashboardStats.data?.month_hours,
		})
	)
}

const handleQRScanSuccess = async (token, position = null) => {
	const action = primaryScanMeta.value?.action
	if (!action) return

	try {
		// 扫码弹窗已按需要定位；服务端还要定位（刚从公司 Wi-Fi 换到流量）时再定位一次
		const result = await submitQrCheckin({
			call: callFrappe,
			token,
			logType: action,
			position,
			locate: () => acquireCheckinLocation(),
		})
		if (result.outcome === "success") {
			await handleCheckinSuccess(action, result.message)
			return
		}
		if (result.outcome === "location_failed") {
			reportLocationFailure(callFrappe, {
				flow: "qr",
				reason: result.reason,
				elapsedMs: result.location?.elapsedMs,
			})
			toast.error(__("Location Error"), {
				description: locationFailureAdvice(result.reason, currentLanguage),
			})
			return
		}
		toast.error(__("Error"), {
			description: result.message || __("Check-in failed"),
		})
	} finally {
		// 无论成功失败，都重置 scanner 的 submitting 状态
		if (qrScannerRef.value) {
			qrScannerRef.value.submitting = false
		}
	}
}

function getReducedMotion() {
	if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false
	try {
		return window.matchMedia("(prefers-reduced-motion: reduce)").matches
	} catch (_) {
		return false
	}
}

function replayIntro() {
	if (getReducedMotion()) return
	introPlay.value = false
	requestAnimationFrame(() => {
		requestAnimationFrame(() => {
			introPlay.value = true
		})
	})
}

function onVisibilityChange() {
	if (typeof document === "undefined") return
	if (document.visibilityState === "visible") {
		replayIntro()
	}
}

onMounted(() => {
	loadHomeScheduleSummary()
	detectPlatformSupport()
	const storage = typeof window !== "undefined" ? window.sessionStorage : null
	const matchMedia = typeof window !== "undefined" ? window.matchMedia.bind(window) : null
	if (shouldPlayIntro({ storage, matchMedia })) {
		introPlay.value = true
		markIntroPlayed({ storage })
	}
	if (typeof document !== "undefined") {
		document.addEventListener("visibilitychange", onVisibilityChange)
	}
})

onIonViewWillEnter(() => {
	loadHomeScheduleSummary()
	passkeyContext.reload()
})

onBeforeUnmount(() => {
	successOverlayController.dispose()
	if (typeof document !== "undefined") {
		document.removeEventListener("visibilitychange", onVisibilityChange)
	}
})

// 辅助函数
function getGreeting() {
	const hour = new Date().getHours()
	const lang = currentLanguage

	const greetings = {
		ja: {
			morning: "おはようございます",
			afternoon: "こんにちは",
			evening: "こんばんは",
		},
		zh: {
			morning: "早上好",
			afternoon: "下午好",
			evening: "晚上好",
		},
		en: {
			morning: "Good morning",
			afternoon: "Good afternoon",
			evening: "Good evening",
		},
	}

	const langGreetings = greetings[lang] || greetings.zh

	if (hour < 12) return langGreetings.morning
	if (hour < 18) return langGreetings.afternoon
	return langGreetings.evening
}

function formatDate() {
	const lang = currentLanguage
	const date = new Date()

	if (lang === "ja") {
		return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 (${
			["日", "月", "火", "水", "木", "金", "土"][date.getDay()]
		})`
	} else if (lang === "zh") {
		return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 星期${
			["日", "一", "二", "三", "四", "五", "六"][date.getDay()]
		}`
	} else {
		return dayjs().format("ddd, D MMMM, YYYY")
	}
}
</script>

<style scoped>
.checkin-panel {
	display: flex;
	flex-direction: column;
	gap: 14px;
	width: 100%;
	flex: 1;
	padding-bottom: 110px;
}

.home-sale-banner {
	display: flex;
	align-items: center;
	gap: 14px;
	width: 100%;
	border: 2px solid;
	border-radius: 20px;
	padding: 14px 18px;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 24px rgba(15, 23, 42, 0.06);
}

.home-sale-dot {
	width: 14px;
	height: 14px;
	border-radius: 999px;
	background: currentColor;
	box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.78);
	flex: 0 0 auto;
}

.home-sale-copy {
	display: grid;
	gap: 3px;
	min-width: 0;
}

.home-sale-copy strong {
	font-size: 17px;
	line-height: 1.12;
	font-weight: 900;
}

.home-sale-copy span {
	font-size: 16px;
	line-height: 1.18;
	font-weight: 800;
	opacity: 0.82;
	overflow-wrap: anywhere;
}

@media (prefers-reduced-motion: no-preference) {
	.checkin-panel.intro-play .intro-stagger {
		opacity: 0;
		transform: translateY(12px);
		animation: ckp-stagger-in 640ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}
	.checkin-panel.intro-play .intro-stagger-0 {
		animation-delay: 0ms;
	}
	.checkin-panel.intro-play .intro-stagger-1 {
		animation-delay: 0ms;
	}
	.checkin-panel.intro-play .intro-stagger-2 {
		animation-delay: 150ms;
	}
	.checkin-panel.intro-play .intro-stagger-3 {
		animation-delay: 300ms;
	}
}

@keyframes ckp-stagger-in {
	to {
		opacity: 1;
		transform: translateY(0);
	}
}
</style>
