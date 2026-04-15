<template>
	<div class="checkin-panel">
		<!-- 工作状态卡片 -->
		<div
			v-if="resolvedWorkStatus !== null"
			:class="[
				'w-full rounded-lg px-4 py-3 flex items-center gap-3 shadow-sm transition-all duration-300',
				resolvedWorkStatus
					? 'bg-gradient-to-r from-green-500 to-green-600'
					: 'bg-gradient-to-r from-gray-500 to-gray-600'
			]"
		>
			<span
				:class="[
					'w-2.5 h-2.5 rounded-full flex-shrink-0',
					resolvedWorkStatus ? 'bg-white animate-pulse' : 'bg-gray-300'
				]"
			></span>
			<span class="text-white font-semibold text-sm">{{ getStatusText() }}</span>
		</div>

		<!-- 欢迎和打卡 -->
		<div class="bg-white rounded-lg p-4 shadow-sm">
		<h2 class="text-lg font-bold text-gray-900">
				{{ getGreeting() }} {{ employee?.data?.first_name }}さん 👋
		</h2>
			<div class="font-medium text-sm text-gray-500 mt-1 mb-3">
				{{ formatDate() }}
			</div>

			<!-- 扫码打卡按钮 -->
			<template v-if="settings.data?.allow_employee_checkin_from_mobile_app">
				<button
					v-if="primaryScanMeta"
					class="checkin-btn"
					@click="openQRScanner"
				>
					<div class="checkin-btn-content">
						<svg class="checkin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M3 7V5a2 2 0 0 1 2-2h2"/>
							<path d="M17 3h2a2 2 0 0 1 2 2v2"/>
							<path d="M21 17v2a2 2 0 0 1-2 2h-2"/>
							<path d="M7 21H5a2 2 0 0 1-2-2v-2"/>
							<rect x="7" y="7" width="10" height="10" rx="1"/>
						</svg>
						<div class="checkin-text">
							<span class="checkin-title">{{ primaryScanMeta.title }}</span>
							<span class="checkin-desc">{{ primaryScanMeta.description }}</span>
						</div>
					</div>
					<svg class="checkin-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M9 18l6-6-6-6"/>
					</svg>
				</button>

				<div class="font-medium text-xs text-gray-400 mt-3 text-center" v-if="lastLog">
					<span>{{ __("Last {0} was at {1}", [__(lastLogType), formatTimestamp(lastLog.time)]) }}</span>
					<span class="whitespace-pre"> · </span>
					<router-link :to="{ name: 'EmployeeCheckinListView' }" v-slot="{ navigate }">
						<span @click="navigate" class="underline text-blue-500">{{ __("View List") }}</span>
					</router-link>
				</div>
			</template>
		</div>

		<!-- 排班提醒 -->
		<HomeSummaryCard />

		<!-- 天气卡片 -->
		<WeatherWidget />

		<!-- 统计卡片 -->
		<div v-if="dashboardStats.data" class="stats-row">
			<div class="stat-card hours">
				<div class="stat-value">{{ formatHours(dashboardStats.data.month_hours) }}</div>
				<div class="stat-label">{{ getStatsLabel('month_hours') }}</div>
			</div>
			<div class="stat-card present">
				<div class="stat-value">{{ dashboardStats.data.month_present }}</div>
				<div class="stat-label">{{ getStatsLabel('month_present') }}</div>
			</div>
		</div>

		<!-- 最新通知卡片 -->
		<router-link :to="{ name: 'Notifications' }" class="notification-card" v-if="latestNotification.data">
			<div class="notification-header">
				<div class="notification-icon">
					<FeatherIcon name="bell" class="w-4 h-4" />
				</div>
				<span class="notification-title">{{ getNotificationTitle() }}</span>
				<FeatherIcon name="chevron-right" class="w-4 h-4 text-gray-400" />
			</div>
			<div class="notification-content" v-if="getNotificationDisplayMessage()">
				<div class="notification-message prose prose-sm" v-html="truncateHtml(getNotificationDisplayMessage(), 80)"></div>
				<div class="notification-time">{{ formatNotificationTime(latestNotification.data.creation) }}</div>
			</div>
			<div class="notification-empty" v-else>
				{{ getNoNotificationText() }}
			</div>
		</router-link>
	</div>

	<ion-modal
		v-if="settings.data?.allow_employee_checkin_from_mobile_app"
		ref="modal"
		trigger="open-checkin-modal"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="h-120 w-full flex flex-col items-center justify-center gap-5 p-4 mb-5">
			<div class="flex flex-col gap-1.5 mt-2 items-center justify-center">
				<div class="font-bold text-xl">
					{{ dayjs(checkinTimestamp).format("hh:mm:ss a") }}
				</div>
				<div class="font-medium text-gray-500 text-sm">
					{{ dayjs().format("D MMM, YYYY") }}
				</div>
			</div>

			<template v-if="settings.data?.allow_geolocation_tracking">
				<span v-if="locationStatus" class="font-medium text-gray-500 text-sm">
					{{ locationStatus }}
				</span>

				<div class="rounded border-4 translate-z-0 block overflow-hidden w-full h-170">
					<iframe
						width="100%"
						height="170"
						frameborder="0"
						scrolling="no"
						marginheight="0"
						marginwidth="0"
						style="border: 0"
						:src="`https://maps.google.com/maps?q=${latitude},${longitude}&hl=en&z=15&amp;output=embed`"
					>
					</iframe>
				</div>
			</template>

			<Button
				v-if="primaryScanMeta"
				:loading="checkins.insert.loading"
				variant="solid"
				class="w-full py-5 text-sm disabled:bg-gray-700"
				@click="submitLog(primaryScanMeta.action)"
			>
				{{ __("Confirm {0}", [primaryScanMeta.label]) }}
			</Button>
		</div>
	</ion-modal>

	<!-- 扫码模态框 -->
	<QRScannerModal
		v-if="primaryScanMeta"
		ref="qrScannerRef"
		:is-open="showQRScanner"
		:log-type="primaryScanMeta.action"
		@close="showQRScanner = false"
		@success="handleQRScanSuccess"
	/>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue"
import { IonModal, modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"
import {
	getPrimaryScanMeta,
	resolveWorkStatusValue,
} from "@/utils/homeExperience"
import QRScannerModal from "@/components/QRScannerModal.vue"
import WeatherWidget from "@/components/WeatherWidget.vue"
import HomeSummaryCard from "@/components/work_roster/HomeSummaryCard.vue"

const DOCTYPE = "Employee Checkin"

const props = defineProps({
	workStatus: {
		type: Object,
		required: true,
	},
})

const socket = inject("$socket")
const employee = inject("$employee")
const dayjs = inject("$dayjs")
const __ = inject("$translate")
const checkinTimestamp = ref(null)
const latitude = ref(0)
const longitude = ref(0)
const locationStatus = ref("")
const showQRScanner = ref(false)
const qrScannerRef = ref(null)
const lang = computed(() => window.frappe?.boot?.lang || "zh")
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

const checkins = createListResource({
	doctype: DOCTYPE,
	fields: ["name", "employee", "employee_name", "log_type", "time", "device_id"],
	filters: {
		employee: employee.data.name,
	},
	orderBy: "time desc",
})
checkins.reload()

const lastLog = computed(() => {
	if (checkins.list.loading || !checkins.data) return {}
	return checkins.data[0]
})

const lastLogType = computed(() => {
	return lastLog?.value?.log_type === "IN" ? "check-in" : "check-out"
})

const resolvedWorkStatus = computed(() =>
	resolveWorkStatusValue(props.workStatus?.data),
)

const primaryScanMeta = computed(() =>
	getPrimaryScanMeta(resolvedWorkStatus.value, lang.value, __),
)

function handleLocationSuccess(position) {
	latitude.value = position.coords.latitude
	longitude.value = position.coords.longitude

	locationStatus.value = [
		__("Latitude: {0}°", [Number(latitude.value).toFixed(5)]),
		__("Longitude: {0}°", [Number(longitude.value).toFixed(5)]),
	].join(", ")
}

function handleLocationError(error) {
	locationStatus.value = __("Unable to retrieve your location")
	if (error) locationStatus.value += `: ERROR(${error.code}): ${error.message}`
}

const fetchLocation = () => {
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
	} else {
		locationStatus.value = __("Locating...")
		navigator.geolocation.getCurrentPosition(handleLocationSuccess, handleLocationError)
	}
}

const handleEmployeeCheckin = () => {
	checkinTimestamp.value = dayjs().format("YYYY-MM-DD HH:mm:ss")

	if (settings.data?.allow_geolocation_tracking) {
		fetchLocation()
	}
}

const submitLog = (logType) => {
	const actionLabel = logType === "IN" ? __("Check-in") : __("Check-out")

	checkins.insert.submit(
		{
			employee: employee.data.name,
			log_type: logType,
			time: checkinTimestamp.value,
			latitude: latitude.value,
			longitude: longitude.value,
		},
		{
			onSuccess() {
				// 发送全局事件通知工作状态徽章更新
				window.dispatchEvent(new CustomEvent("checkin-status-changed", {
					detail: { log_type: logType }
				}))
				
				modalController.dismiss()
				toast({
					title: __("Success"),
					text: __("{0} successful!", [actionLabel]),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			},
			onError(error) {
				let messages = error.messages || []

				for (const message of messages) {
					toast({
						title: __("Error"),
						text: message || __("{0} failed!", [actionLabel]),
						icon: "alert-circle",
						position: "bottom-center",
						iconClasses: "text-red-500",
					})
				}
			},
		}
	)
}

const openQRScanner = () => {
	if (!primaryScanMeta.value) return
	showQRScanner.value = true
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
					
					navigator.geolocation.getCurrentPosition(
						resolve,
						reject,
						{
							enableHighAccuracy: true,
							timeout: 10000,
							maximumAge: 0
						}
					)
				})
				
				latitude = position.coords.latitude
				longitude = position.coords.longitude
			} catch (geoError) {
				toast({
					title: __("Location Error"),
					text: __("Unable to retrieve your location. Please enable location access and try again."),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500"
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
				"X-Frappe-CSRF-Token": window.csrf_token || ""
			},
			body: JSON.stringify({
				token: token,
				log_type: action,
				latitude: latitude,
				longitude: longitude
			})
		})

		const data = await response.json()

		// 检查是否成功
		if (response.ok && data.message && data.message.status === "ok") {
			toast({
				title: __("Success"),
				text: data.message.message,
				icon: "check-circle",
				position: "bottom-center",
				iconClasses: "text-green-500"
			})
			
			// 刷新打卡记录列表
			checkins.reload()
			
			// 发送全局事件通知工作状态徽章更新
			window.dispatchEvent(new CustomEvent("checkin-status-changed", {
				detail: { log_type: action }
			}))
			
			// 关闭扫码窗口
			showQRScanner.value = false
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
			iconClasses: "text-red-500"
		})
	} finally {
		// 无论成功失败，都重置 scanner 的 submitting 状态
		if (qrScannerRef.value) {
			qrScannerRef.value.submitting = false
		}
	}
}

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype == DOCTYPE) {
			checkins.reload()
		}
	})
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
})

// 辅助函数
function getGreeting() {
	const hour = new Date().getHours()
	const lang = frappe.boot.lang || "ja"
	
	const greetings = {
		ja: {
			morning: "おはようございます",
			afternoon: "こんにちは",
			evening: "こんばんは"
		},
		zh: {
			morning: "早上好",
			afternoon: "下午好",
			evening: "晚上好"
		},
		en: {
			morning: "Good morning",
			afternoon: "Good afternoon",
			evening: "Good evening"
		}
	}
	
	const langGreetings = greetings[lang] || greetings.ja
	
	if (hour < 12) return langGreetings.morning
	if (hour < 18) return langGreetings.afternoon
	return langGreetings.evening
}

function formatDate() {
	const lang = frappe.boot.lang || "ja"
	const date = new Date()
	
	if (lang === "ja") {
		return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 (${['日', '月', '火', '水', '木', '金', '土'][date.getDay()]})`
	} else if (lang === "zh") {
		return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 星期${['日', '一', '二', '三', '四', '五', '六'][date.getDay()]}`
	} else {
		return dayjs().format("ddd, D MMMM, YYYY")
	}
}

function formatHours(hours) {
	if (!hours) return "0.00"
	return hours.toFixed(2)
}

function getStatsLabel(key) {
	const lang = frappe.boot.lang || "ja"
	
	const labels = {
		today_hours: {
			ja: "今日の勤務時間",
			zh: "今日工作时长",
			en: "Today's Hours"
		},
		month_hours: {
			ja: "今月の勤務時間",
			zh: "本月工作时长",
			en: "This Month"
		},
		month_present: {
			ja: "今月の出勤",
			zh: "本月出勤",
			en: "Days Present"
		},
		month_absent: {
			ja: "今月の休み",
			zh: "本月休息",
			en: "Days Rest"
		},
		hours_unit: {
			ja: "時間",
			zh: "小时",
			en: "hours"
		},
		days_unit: {
			ja: "日",
			zh: "天",
			en: "days"
		}
	}
	
	return labels[key]?.[lang] || labels[key]?.ja || key
}

function getStatusText() {
	if (resolvedWorkStatus.value === null) return ""
	
	const lang = frappe.boot?.lang || "ja"
	
	if (resolvedWorkStatus.value) {
		if (lang === "ja") return "勤務中"
		if (lang === "zh") return "上班中"
		return "Working"
	} else {
		if (lang === "ja") return "退勤済"
		if (lang === "zh") return "已下班"
		return "Off Work"
	}
}

function getNotificationTitle() {
	const lang = frappe.boot?.lang || "ja"
	if (lang === "ja") return "お知らせ"
	if (lang === "zh") return "最新通知"
	return "Notifications"
}

function getNoNotificationText() {
	const lang = frappe.boot?.lang || "ja"
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
	const diffMinutes = now.diff(date, 'minute')
	const diffHours = now.diff(date, 'hour')
	const diffDays = now.diff(date, 'day')
	
	const lang = frappe.boot?.lang || "ja"
	
	if (diffMinutes < 1) {
		return lang === "ja" ? "たった今" : lang === "zh" ? "刚刚" : "Just now"
	} else if (diffMinutes < 60) {
		return lang === "ja" ? `${diffMinutes}分前` : lang === "zh" ? `${diffMinutes}分钟前` : `${diffMinutes}m ago`
	} else if (diffHours < 24) {
		return lang === "ja" ? `${diffHours}時間前` : lang === "zh" ? `${diffHours}小时前` : `${diffHours}h ago`
	} else if (diffDays < 7) {
		return lang === "ja" ? `${diffDays}日前` : lang === "zh" ? `${diffDays}天前` : `${diffDays}d ago`
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
	box-shadow: 0 2px 8px rgba(0,0,0,0.05);
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

@keyframes pulse {
	0%, 100% {
		opacity: 1;
	}
	50% {
		opacity: 0.5;
	}
}

.animate-pulse {
	animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* 扫码打卡按钮 */
.checkin-btn {
	width: 100%;
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 20px;
	background: rgba(37, 99, 235, 0.08);
	border: 1px solid rgba(37, 99, 235, 0.3);
	border-radius: 12px;
	cursor: pointer;
	transition: all 0.2s ease;
}

.checkin-btn:hover {
	background: #2563EB;
	border-color: #2563EB;
}

.checkin-btn:hover .checkin-icon,
.checkin-btn:hover .checkin-title,
.checkin-btn:hover .checkin-arrow {
	color: white;
}

.checkin-btn:hover .checkin-desc {
	color: rgba(255, 255, 255, 0.8);
}

.checkin-btn:active {
	background: #1d4ed8;
	transform: scale(0.99);
}

.checkin-btn-content {
	display: flex;
	align-items: center;
	gap: 14px;
}

.checkin-icon {
	width: 28px;
	height: 28px;
	color: #2563EB;
	flex-shrink: 0;
	transition: color 0.2s ease;
}

.checkin-text {
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	gap: 2px;
}

.checkin-title {
	font-size: 16px;
	font-weight: 700;
	color: #2563EB;
	line-height: 1.3;
	transition: color 0.2s ease;
}

.checkin-desc {
	font-size: 12px;
	color: #9CA3AF;
	line-height: 1.3;
	transition: color 0.2s ease;
}

.checkin-arrow {
	width: 20px;
	height: 20px;
	color: rgba(37, 99, 235, 0.5);
	flex-shrink: 0;
	transition: color 0.2s ease;
}

/* 通知卡片 */
.notification-card {
	display: block;
	background: white;
	border-radius: 14px;
	padding: 14px 16px;
	box-shadow: 0 2px 8px rgba(0,0,0,0.05);
	text-decoration: none;
	transition: all 0.2s ease;
	border-left: 4px solid #f59e0b;
}

.notification-card:hover {
	box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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
