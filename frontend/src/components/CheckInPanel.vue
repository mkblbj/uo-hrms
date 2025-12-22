<template>
	<div class="flex flex-col bg-gray-50 rounded w-full py-6 px-4 border-none gap-3">
		<!-- 工作状态卡片 -->
		<div
			v-if="workStatus.data"
			:class="[
				'w-full rounded-lg px-4 py-3 flex items-center gap-3 shadow-sm transition-all duration-300',
				workStatus.data.is_working
					? 'bg-gradient-to-r from-green-500 to-green-600'
					: 'bg-gradient-to-r from-gray-500 to-gray-600'
			]"
		>
			<span
				:class="[
					'w-2.5 h-2.5 rounded-full flex-shrink-0',
					workStatus.data.is_working ? 'bg-white animate-pulse' : 'bg-gray-300'
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
							<span class="checkin-title">{{ getCheckinButtonText() }}</span>
							<span class="checkin-desc">{{ getCheckinButtonDesc() }}</span>
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

		<!-- 天气卡片 -->
		<WeatherWidget />

		<!-- 统计卡片 - 只显示2个 -->
		<div v-if="dashboardStats.data" class="stats-grid-compact">
			<StatsCard
				:label="getStatsLabel('month_hours')"
				:value="formatHours(dashboardStats.data.month_hours)"
				:subtitle="getStatsLabel('hours_unit')"
				icon="clock"
				color="purple"
			/>
			<StatsCard
				:label="getStatsLabel('month_present')"
				:value="dashboardStats.data.month_present"
				:subtitle="getStatsLabel('days_unit')"
				icon="check-circle"
				color="green"
			/>
		</div>
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

			<Button :loading="checkins.insert.loading" variant="solid" class="w-full py-5 text-sm disabled:bg-gray-700" @click="submitLog(nextAction.action)">
				{{ __("Confirm {0}", [nextAction.label]) }}
			</Button>
		</div>
	</ion-modal>

	<!-- 扫码模态框 -->
	<QRScannerModal
		ref="qrScannerRef"
		:is-open="showQRScanner"
		:log-type="nextAction.action"
		@close="showQRScanner = false"
		@success="handleQRScanSuccess"
	/>
</template>

<script setup>
import { createResource, createListResource, toast, FeatherIcon } from "frappe-ui"
import { computed, inject, ref, onMounted, onBeforeUnmount } from "vue"
import { IonModal, modalController } from "@ionic/vue"

import { formatTimestamp } from "@/utils/formatters"
import QRScannerModal from "@/components/QRScannerModal.vue"
import WeatherWidget from "@/components/WeatherWidget.vue"
import StatsCard from "@/components/StatsCard.vue"

const DOCTYPE = "Employee Checkin"

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
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const dashboardStats = createResource({
	url: "hrms.api.get_employee_dashboard_stats",
	auto: true,
})

const workStatus = createResource({
	url: "hrms.api.get_employee_work_status",
	auto: true,
	cache: false,
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

const nextAction = computed(() => {
	return lastLog?.value?.log_type === "IN"
		? { action: "OUT", label: __("Check Out") }
		: { action: "IN", label: __("Check In") }
})

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
	showQRScanner.value = true
}

const handleQRScanSuccess = async (token, latitude = null, longitude = null) => {
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
				log_type: nextAction.value.action,
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
				detail: { log_type: nextAction.value.action }
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

// 监听打卡状态变化事件
const handleCheckinStatusChange = () => {
	workStatus.reload()
}

// 每30秒刷新一次工作状态
let refreshInterval = null

onMounted(() => {
	socket.emit("doctype_subscribe", DOCTYPE)
	socket.on("list_update", (data) => {
		if (data.doctype == DOCTYPE) {
			checkins.reload()
		}
	})
	
	// 定时刷新工作状态
	refreshInterval = setInterval(() => {
		workStatus.reload()
	}, 30000)
	
	// 监听打卡事件
	window.addEventListener('checkin-status-changed', handleCheckinStatusChange)
})

onBeforeUnmount(() => {
	socket.emit("doctype_unsubscribe", DOCTYPE)
	socket.off("list_update")
	
	if (refreshInterval) {
		clearInterval(refreshInterval)
	}
	window.removeEventListener('checkin-status-changed', handleCheckinStatusChange)
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
	if (!hours) return "0"
	return hours.toFixed(1)
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
			ja: "今月の欠勤",
			zh: "本月缺勤",
			en: "Days Absent"
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
	if (!workStatus.data) return ""
	
	const lang = frappe.boot?.lang || "ja"
	
	if (workStatus.data.is_working) {
		if (lang === "ja") return "勤務中"
		if (lang === "zh") return "上班中"
		return "Working"
	} else {
		if (lang === "ja") return "退勤済"
		if (lang === "zh") return "已下班"
		return "Off Work"
	}
}

function getCheckinButtonText() {
	const lang = frappe.boot?.lang || "ja"
	const isCheckIn = nextAction.value.action === "IN"
	
	if (lang === "ja") {
		return isCheckIn ? "QRコードで出勤" : "QRコードで退勤"
	} else if (lang === "zh") {
		return isCheckIn ? "扫码签到" : "扫码签退"
	}
	return isCheckIn ? "Scan QR to Check In" : "Scan QR to Check Out"
}

function getCheckinButtonDesc() {
	const lang = frappe.boot?.lang || "ja"
	const isCheckIn = nextAction.value.action === "IN"
	
	if (lang === "ja") {
		return isCheckIn ? "カメラを起動して出勤打刻します" : "カメラを起動して退勤打刻します"
	} else if (lang === "zh") {
		return "启动相机扫描二维码打卡"
	}
	return "Open camera to scan QR code"
}
</script>

<style scoped>
.stats-grid-compact {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 10px;
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
</style>
