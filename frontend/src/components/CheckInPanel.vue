<template>
	<div class="checkin-panel" :class="{ 'intro-play': introPlay }">
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
		<HomeStatsGrid class="intro-stagger intro-stagger-3" :stats="dashboardStats.data" :lang="currentLanguage" />
	</div>

	<HomeScanActionBar
		:cta="primaryScanMeta"
		:work-status="props.workStatus?.data"
		:lang="currentLanguage"
		:disabled="!isMobileCheckinAllowed"
		@scan="openQRScanner"
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
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import CheckinSuccessOverlay from "@/components/home/CheckinSuccessOverlay.vue"
import HomeHeroCard from "@/components/home/HomeHeroCard.vue"
import HomeScanActionBar from "@/components/home/HomeScanActionBar.vue"
import HomeStatsGrid from "@/components/home/HomeStatsGrid.vue"
import QRScannerModal from "@/components/QRScannerModal.vue"
import HomeSummaryCard from "@/components/work_roster/HomeSummaryCard.vue"
import { formatTimestamp } from "@/utils/formatters"
import {
	buildSuccessOverlayModel,
	emitCheckinStatusChanged,
	getHeroCardMeta,
	resolveHomeLanguage,
} from "@/utils/homeExperience"
import { shouldPlayIntro, markIntroPlayed } from "@/utils/homeIntroAnimation"

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
const successOverlayState = reactive({
	isOpen: false,
	actionsVisible: false,
	model: null,
	returnRoute: null,
})
const successOverlayController = createSuccessOverlayController({
	state: successOverlayState,
})
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
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

const openQRScanner = () => {
	if (!settings.data?.allow_employee_checkin_from_mobile_app || !primaryScanMeta.value) return
	showQRScanner.value = true
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

const handleQRScanSuccess = async (token, latitude = null, longitude = null) => {
	const action = primaryScanMeta.value?.action
	if (!action) return

	try {
		// 如果启用了地理位置追踪，但扫码模态框没有传递位置信息，则尝试获取
		if (settings.data?.allow_geolocation_tracking && (!latitude || !longitude)) {
			try {
				const position = await new Promise((resolve, reject) => {
					if (!navigator.geolocation) {
						reject(new Error(__("Geolocation is not supported by your browser")))
						return
					}

					navigator.geolocation.getCurrentPosition(resolve, reject, {
						enableHighAccuracy: true,
						timeout: 10000,
						maximumAge: 0,
					})
				})

				latitude = position.coords.latitude
				longitude = position.coords.longitude
			} catch (geoError) {
				toast({
					title: __("Location Error"),
					text: __(
						"Unable to retrieve your location. Please enable location access and try again."
					),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
				// 重置 scanner 的 submitting 状态
				if (qrScannerRef.value) {
					qrScannerRef.value.submitting = false
				}
				return
			}
		}

		// 调用后端二维码打卡 API
		const response = await fetch("/api/method/hrms.api.qr_attendance.qr_checkin", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
			body: JSON.stringify({
				token: token,
				log_type: action,
				latitude: latitude,
				longitude: longitude,
			}),
		})

		const data = await response.json()

		// 检查是否成功
		if (response.ok && data.message && data.message.status === "ok") {
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
			// iOS PWA: 等待 QR scanner 的 ion-modal 开始 dismiss 后再开启 success overlay，
			// 避免两个 ion-modal 的进出场动画重叠导致子 CSS 动画被 WebKit 合成器冻结。
			await new Promise((resolve) => setTimeout(resolve, 320))
			openSuccessOverlay(
				buildSuccessOverlayModel({
					action,
					lang: currentLanguage,
					responseMessage: data.message,
					monthHours: dashboardStats.data?.month_hours,
				})
			)
			return
		} else {
			// 处理错误：优先显示后端返回的友好错误信息
			let errorMessage = __("Check-in failed")

			// Frappe 错误格式解析
			if (data._server_messages) {
				try {
					const messages = JSON.parse(data._server_messages)
					if (messages && messages.length > 0) {
						const msg = JSON.parse(messages[0])
						errorMessage = msg.message || errorMessage
					}
				} catch (e) {
					console.error("Failed to parse error messages", e)
				}
			} else if (data.exception) {
				// 从 exception 中提取错误信息
				const match = data.exception.match(/frappe\.exceptions\.\w+:\s*(.+)/)
				if (match && match[1]) {
					errorMessage = match[1].trim()
				}
			} else if (data.exc) {
				// 兼容旧版本
				errorMessage = data.exc
			}

			throw new Error(errorMessage)
		}
	} catch (error) {
		toast({
			title: __("Error"),
			text: error.message || __("Check-in failed"),
			icon: "alert-circle",
			position: "bottom-center",
			iconClasses: "text-red-500",
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

@media (prefers-reduced-motion: no-preference) {
	.checkin-panel.intro-play .intro-stagger {
		opacity: 0;
		transform: translateY(12px);
		animation: ckp-stagger-in 640ms cubic-bezier(0.22, 1, 0.36, 1) forwards;
	}
	.checkin-panel.intro-play .intro-stagger-1 { animation-delay: 0ms; }
	.checkin-panel.intro-play .intro-stagger-2 { animation-delay: 150ms; }
	.checkin-panel.intro-play .intro-stagger-3 { animation-delay: 300ms; }
}

@keyframes ckp-stagger-in {
	to { opacity: 1; transform: translateY(0); }
}
</style>
