<template>
	<div class="checkin-panel">
		<HomeHeroCard
			:employee-name="employee?.data?.first_name || employee?.data?.employee_name || ''"
			:greeting="getGreeting()"
			:date-label="formatDate()"
			:summary="heroSummary"
			:cta="primaryScanMeta"
			@scan="openQRScanner"
		/>

		<HomeSummaryCard :lang="currentLanguage" />
		<WeatherWidget :lang="currentLanguage" />

		<div v-if="dashboardStats.data" class="stats-row stats-row--subtle">
			<div class="stat-card hours">
				<div class="stat-value">{{ formatHours(dashboardStats.data.month_hours) }}</div>
				<div class="stat-label">{{ getStatsLabel("month_hours") }}</div>
			</div>
			<div class="stat-card present">
				<div class="stat-value">{{ dashboardStats.data.month_present }}</div>
				<div class="stat-label">{{ getStatsLabel("month_present") }}</div>
			</div>
		</div>

		<!-- 最新通知卡片 -->
		<router-link
			:to="{ name: 'Notifications' }"
			class="notification-card"
			v-if="latestNotification.data"
		>
			<div class="notification-header">
				<div class="notification-icon">
					<FeatherIcon name="bell" class="w-4 h-4" />
				</div>
				<span class="notification-title">{{ getNotificationTitle() }}</span>
				<FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400" />
			</div>
			<div class="notification-content" v-if="getNotificationDisplayMessage()">
				<div
					class="notification-message prose prose-sm"
					v-html="truncateHtml(getNotificationDisplayMessage(), 80)"
				></div>
				<div class="notification-time">
					{{ formatNotificationTime(latestNotification.data.creation) }}
				</div>
			</div>
			<div class="notification-empty" v-else>
				{{ getNoNotificationText() }}
			</div>
		</router-link>
	</div>

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
		v-if="successOverlayModel"
		:is-open="successOverlayOpen"
		:actions-visible="successOverlayActionsVisible"
		:model="successOverlayModel"
		@primary="handleSuccessPrimary"
		@close="closeSuccessOverlay"
	/>
</template>

<script setup>
import { createResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, onBeforeUnmount, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import CheckinSuccessOverlay from "@/components/home/CheckinSuccessOverlay.vue"
import QRScannerModal from "@/components/QRScannerModal.vue"
import WeatherWidget from "@/components/WeatherWidget.vue"
import HomeHeroCard from "@/components/home/HomeHeroCard.vue"
import HomeSummaryCard from "@/components/work_roster/HomeSummaryCard.vue"
import { formatTimestamp } from "@/utils/formatters"
import {
	buildSuccessOverlayModel,
	emitCheckinStatusChanged,
	getHeroCardMeta,
	resolveHomeLanguage,
} from "@/utils/homeExperience"

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
const currentLanguage = resolveHomeLanguage(window.frappe?.boot)
const successOverlayOpen = ref(false)
const successOverlayActionsVisible = ref(false)
const successOverlayModel = ref(null)
const returnRoute = ref(null)
let successActionsTimer = null
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const dashboardStats = createResource({
	url: "hrms.api.get_employee_dashboard_stats",
	auto: true,
})

const latestNotification = createResource({
	url: "hrms.api.get_latest_notification",
	auto: true,
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
const heroSummary = computed(() => heroCardMeta.value.summary)

const openQRScanner = () => {
	if (!settings.data?.allow_employee_checkin_from_mobile_app || !primaryScanMeta.value) return
	showQRScanner.value = true
}

function clearSuccessActionsTimer() {
	if (successActionsTimer !== null) {
		window.clearTimeout(successActionsTimer)
		successActionsTimer = null
	}
}

function openSuccessOverlay(model) {
	returnRoute.value = route.fullPath
	successOverlayModel.value = model
	successOverlayActionsVisible.value = false
	successOverlayOpen.value = true
	clearSuccessActionsTimer()
	successActionsTimer = window.setTimeout(() => {
		successOverlayActionsVisible.value = true
	}, model.delayMs)
}

function closeSuccessOverlay() {
	const previousRoute = returnRoute.value
	successOverlayOpen.value = false
	successOverlayActionsVisible.value = false
	successOverlayModel.value = null
	returnRoute.value = null
	clearSuccessActionsTimer()
	if (previousRoute && route.fullPath !== previousRoute) {
		router.replace(previousRoute)
	}
}

function handleSuccessPrimary() {
	const target = successOverlayModel.value?.primaryRoute
	successOverlayOpen.value = false
	successOverlayActionsVisible.value = false
	successOverlayModel.value = null
	returnRoute.value = null
	clearSuccessActionsTimer()
	if (target) router.push(target)
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

			// 发送全局事件通知工作状态徽章更新
			emitCheckinStatusChanged(window, { log_type: action })
			showQRScanner.value = false
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

onBeforeUnmount(() => {
	clearSuccessActionsTimer()
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

function formatHours(hours) {
	if (!hours) return "0.00"
	return hours.toFixed(2)
}

function getStatsLabel(key) {
	const lang = currentLanguage

	const labels = {
		today_hours: {
			ja: "今日の勤務時間",
			zh: "今日工作时长",
			en: "Today's Hours",
		},
		month_hours: {
			ja: "今月の勤務時間",
			zh: "本月工作时长",
			en: "This Month",
		},
		month_present: {
			ja: "今月の出勤",
			zh: "本月出勤",
			en: "Days Present",
		},
		month_absent: {
			ja: "今月の休み",
			zh: "本月休息",
			en: "Days Rest",
		},
		hours_unit: {
			ja: "時間",
			zh: "小时",
			en: "hours",
		},
		days_unit: {
			ja: "日",
			zh: "天",
			en: "days",
		},
	}

	return labels[key]?.[lang] || labels[key]?.zh || key
}

function getNotificationTitle() {
	const lang = currentLanguage
	if (lang === "ja") return "お知らせ"
	if (lang === "zh") return "最新通知"
	return "Notifications"
}

function getNoNotificationText() {
	const lang = currentLanguage
	if (lang === "ja") return "新しいお知らせはありません"
	if (lang === "zh") return "暂无新通知"
	return "No new notifications"
}

function stripHtml(html) {
	if (!html) return ""
	const tmp = document.createElement("div")
	tmp.innerHTML = html
	const text = tmp.textContent || tmp.innerText || ""
	// 截取前50个字符
	return text.length > 50 ? text.substring(0, 50) + "..." : text
}

function getNotificationDisplayMessage() {
	const data = latestNotification.data
	if (!data) return ""
	// 优先使用 API 返回的 display_message
	if (data.display_message) return data.display_message
	// 如果使用 HTML 源代码模式
	if (data.use_html_source && data.html_source) {
		return data.html_source
	}
	return data.message || ""
}

function truncateHtml(html, maxLength) {
	if (!html) return ""
	const tmp = document.createElement("div")
	tmp.innerHTML = html
	const text = tmp.textContent || tmp.innerText || ""

	// 如果纯文本内容较短，直接返回原 HTML
	if (text.length <= maxLength) {
		return html
	}

	// 否则截取并保留基本 HTML 结构
	// 简单处理：截取文本并保留第一个段落或元素的样式
	const truncatedText = text.substring(0, maxLength) + "..."

	// 尝试保留简单的 HTML 格式
	const firstTag = html.match(/^<(\w+)[^>]*>/)
	if (firstTag) {
		const tagName = firstTag[1]
		return `<${tagName}>${truncatedText}</${tagName}>`
	}

	return truncatedText
}

function formatNotificationTime(dateStr) {
	if (!dateStr) return ""
	const date = dayjs(dateStr)
	const now = dayjs()
	const diffMinutes = now.diff(date, "minute")
	const diffHours = now.diff(date, "hour")
	const diffDays = now.diff(date, "day")

	const lang = currentLanguage

	if (diffMinutes < 1) {
		return lang === "ja" ? "たった今" : lang === "zh" ? "刚刚" : "Just now"
	} else if (diffMinutes < 60) {
		return lang === "ja"
			? `${diffMinutes}分前`
			: lang === "zh"
			? `${diffMinutes}分钟前`
			: `${diffMinutes}m ago`
	} else if (diffHours < 24) {
		return lang === "ja"
			? `${diffHours}時間前`
			: lang === "zh"
			? `${diffHours}小时前`
			: `${diffHours}h ago`
	} else if (diffDays < 7) {
		return lang === "ja"
			? `${diffDays}日前`
			: lang === "zh"
			? `${diffDays}天前`
			: `${diffDays}d ago`
	} else {
		return date.format("MM/DD")
	}
}
</script>

<style scoped>
.checkin-panel {
	display: flex;
	flex-direction: column;
	gap: 16px;
	width: 100%;
	flex: 1;
}
.stats-row {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 12px;
}
.stat-card {
	background: white;
	border-radius: 14px;
	padding: 20px 16px;
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
	border-left: 4px solid;
}
.stat-card.hours {
	border-color: #8b5cf6;
}
.stat-card.present {
	border-color: #10b981;
}
.stat-value {
	font-size: 32px;
	font-weight: 700;
	color: #111827;
	line-height: 1;
}
.stat-label {
	font-size: 13px;
	color: #6b7280;
	margin-top: 8px;
}

.stats-row--subtle .stat-card {
	box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
	padding: 16px 14px;
}

.stats-row--subtle .stat-value {
	font-size: 28px;
}

/* 通知卡片 */
.notification-card {
	display: block;
	background: white;
	border-radius: 14px;
	padding: 14px 16px;
	box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
	text-decoration: none;
	transition: all 0.2s ease;
	border-left: 3px solid #f59e0b;
}

.notification-card:hover {
	box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	transform: translateY(-1px);
}

.notification-card:active {
	transform: translateY(0);
}

.notification-header {
	display: flex;
	align-items: center;
	gap: 8px;
}

.notification-icon {
	width: 28px;
	height: 28px;
	border-radius: 8px;
	background: rgba(245, 158, 11, 0.1);
	display: flex;
	align-items: center;
	justify-content: center;
	color: #f59e0b;
}

.notification-title {
	flex: 1;
	font-size: 14px;
	font-weight: 600;
	color: #374151;
}

.notification-content {
	margin-top: 10px;
	padding-left: 36px;
}

.notification-message {
	font-size: 13px;
	color: #6b7280;
	line-height: 1.5;
	word-break: break-word;
}

.notification-message :deep(h1),
.notification-message :deep(h2),
.notification-message :deep(h3) {
	font-size: 14px;
	font-weight: 600;
	margin: 0 0 4px 0;
	color: #374151;
}

.notification-message :deep(p) {
	margin: 0;
}

.notification-message :deep(strong) {
	font-weight: 600;
}

.notification-message :deep(a) {
	color: #2563eb;
	text-decoration: underline;
}

.notification-message :deep(ul),
.notification-message :deep(ol) {
	margin: 4px 0;
	padding-left: 16px;
}

.notification-message :deep(img) {
	max-width: 100%;
	max-height: 60px;
	border-radius: 4px;
	margin: 4px 0;
}

.notification-time {
	font-size: 11px;
	color: #9ca3af;
	margin-top: 4px;
}

.notification-empty {
	margin-top: 8px;
	padding-left: 36px;
	font-size: 13px;
	color: #9ca3af;
}
</style>
