<template>
	<ion-modal
		:is-open="isOpen"
		@didDismiss="handleDismiss"
		:initial-breakpoint="1"
		:breakpoints="[0, 1]"
	>
		<div class="h-full w-full flex flex-col bg-white">
			<!-- 头部 -->
			<div class="flex items-center justify-between p-4 border-b">
				<h2 class="text-lg font-bold">
					{{ confirmStep ? getConfirmTitle() : __("Scan QR Code") }}
				</h2>
				<button @click="closeModal" class="text-gray-500">
					<FeatherIcon name="x" class="w-6 h-6" />
				</button>
			</div>

			<!-- 确认步骤 -->
			<template v-if="confirmStep">
				<div class="flex-1 flex flex-col p-4">
					<!-- 操作类型和时间 -->
					<div class="bg-gray-50 rounded-lg p-4 mb-4">
						<div class="flex items-center gap-3 mb-3">
							<div :class="['w-12 h-12 rounded-full flex items-center justify-center', 
								props.logType === 'IN' ? 'bg-green-100' : 'bg-orange-100']">
								<FeatherIcon 
									:name="props.logType === 'IN' ? 'log-in' : 'log-out'" 
									:class="['w-6 h-6', props.logType === 'IN' ? 'text-green-600' : 'text-orange-600']" 
								/>
							</div>
							<div>
								<div class="text-lg font-bold">
									{{ props.logType === 'IN' ? __("Check In") : __("Check Out") }}
								</div>
								<div class="text-sm text-gray-500">
									{{ scannedLocation }}
								</div>
							</div>
						</div>
						
						<div class="flex items-center gap-2 text-gray-600">
							<FeatherIcon name="clock" class="w-4 h-4" />
							<span class="text-base font-medium">{{ currentTimeDisplay }}</span>
						</div>
					</div>

					<!-- 智能时间提示（警告） -->
					<div v-if="timeWarning" class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4 flex items-start gap-2">
						<FeatherIcon name="alert-triangle" class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
						<span class="text-yellow-800 text-sm">{{ timeWarning }}</span>
					</div>

					<!-- 地理位置显示 -->
					<template v-if="allowGeolocationTracking && latitude && longitude">
						<div class="text-sm text-gray-500 mb-2">
							{{ locationStatus }}
						</div>
						<div class="rounded border-2 overflow-hidden w-full h-32 mb-4">
							<iframe
								width="100%"
								height="128"
								frameborder="0"
								scrolling="no"
								style="border: 0"
								:src="`https://maps.google.com/maps?q=${latitude},${longitude}&hl=en&z=15&output=embed`"
							>
							</iframe>
						</div>
					</template>

					<!-- 操作按钮 -->
					<div class="mt-auto flex gap-3">
						<Button
							variant="outline"
							class="flex-1 py-4"
							@click="cancelConfirm"
						>
							{{ __("Cancel") }}
						</Button>
						<Button
							:variant="props.logType === 'IN' ? 'solid' : 'solid'"
							:class="['flex-1 py-4', props.logType === 'IN' ? 'bg-green-600 hover:bg-green-700' : 'bg-orange-600 hover:bg-orange-700']"
							:loading="submitting"
							@click="confirmCheckin"
						>
							{{ props.logType === 'IN' ? __("Confirm Check In") : __("Confirm Check Out") }}
						</Button>
					</div>
				</div>
			</template>

			<!-- 扫码步骤 -->
			<template v-else>
				<!-- 地理位置显示区域 -->
				<template v-if="allowGeolocationTracking">
					<div class="px-4 pt-4 pb-2">
						<span v-if="locationStatus" class="font-medium text-gray-500 text-sm block mb-2">
							{{ locationStatus }}
						</span>

						<div v-if="latitude !== null && longitude !== null && latitude !== 0 && longitude !== 0" class="rounded border-4 translate-z-0 block overflow-hidden w-full h-170 mb-2">
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
					</div>
				</template>

				<!-- 扫码区域 -->
				<div class="flex-1 flex flex-col items-center justify-center p-4">
					<div v-if="!scanning" class="text-center mb-4">
						<p class="text-gray-600">{{ __("Position the QR code within the frame") }}</p>
					</div>
					
					<div id="qr-reader" class="w-full max-w-md rounded-lg overflow-hidden"></div>
					
					<div v-if="resultMessage" class="mt-4 text-center">
						<p :class="resultMessageClass">{{ resultMessage }}</p>
					</div>

					<Button
						v-if="!scanning"
						@click="startScanning"
						variant="solid"
						class="mt-4 w-full max-w-md py-3"
					>
						{{ __("Start Scanning") }}
					</Button>

					<!-- 手电筒控制按钮 -->
					<Button
						v-if="scanning && torchAvailable"
						@click="toggleTorch"
						variant="ghost"
						class="mt-2 w-full max-w-md py-3"
					>
						<template #prefix>
							<FeatherIcon :name="torchOn ? 'zap-off' : 'zap'" class="w-5 h-5" />
						</template>
						{{ torchOn ? __("Turn Off Flashlight") : __("Turn On Flashlight") }}
					</Button>
				</div>
			</template>
		</div>
	</ion-modal>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, inject, computed } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, Button, createResource } from "frappe-ui"
import { Html5Qrcode } from "html5-qrcode"

const __ = inject("$translate")
const dayjs = inject("$dayjs")

const props = defineProps({
	isOpen: Boolean,
	logType: {
		type: String,
		default: "IN"
	}
})

const emit = defineEmits(["close", "success", "error"])

const scanning = ref(false)
const resultMessage = ref("")
const resultMessageClass = ref("text-gray-600")
const latitude = ref(null)
const longitude = ref(null)
const locationStatus = ref("")
const torchOn = ref(false)
const torchAvailable = ref(false)
let html5QrCode = null

// 确认步骤相关
const confirmStep = ref(false)
const scannedToken = ref("")
const scannedLocation = ref("")
const currentTimeDisplay = ref("")
const submitting = ref(false)
let timeUpdateInterval = null

// 获取 HR Settings
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const allowGeolocationTracking = computed(() => {
	return settings.data?.allow_geolocation_tracking || false
})

// 智能时间提示
const timeWarning = computed(() => {
	const hour = new Date().getHours()
	const lang = frappe.boot?.lang || "ja"
	
	// 早上（6:00-12:00）签退 → 警告
	if (hour >= 6 && hour < 12 && props.logType === "OUT") {
		const warnings = {
			ja: "現在は午前中です。本当にチェックアウトしますか？",
			zh: "现在是上午，确定要签退吗？",
			en: "It's morning. Are you sure you want to check out?"
		}
		return warnings[lang] || warnings.ja
	}
	
	// 下午/晚上（14:00-23:00）签到 → 警告
	if (hour >= 14 && hour < 23 && props.logType === "IN") {
		const warnings = {
			ja: "現在は午後/夜です。本当にチェックインしますか？",
			zh: "现在是下午/晚上，确定要签到吗？",
			en: "It's afternoon/evening. Are you sure you want to check in?"
		}
		return warnings[lang] || warnings.ja
	}
	
	return null
})

// 确认弹窗标题
function getConfirmTitle() {
	return props.logType === "IN" ? __("Confirm Check In") : __("Confirm Check Out")
}

// 更新当前时间显示
function updateTimeDisplay() {
	const now = new Date()
	const lang = frappe.boot?.lang || "ja"
	
	if (lang === "ja") {
		currentTimeDisplay.value = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
	} else if (lang === "zh") {
		currentTimeDisplay.value = `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
	} else {
		currentTimeDisplay.value = dayjs(now).format("YYYY-MM-DD HH:mm:ss")
	}
}

// 取消确认，返回扫码
function cancelConfirm() {
	confirmStep.value = false
	scannedToken.value = ""
	scannedLocation.value = ""
	if (timeUpdateInterval) {
		clearInterval(timeUpdateInterval)
		timeUpdateInterval = null
	}
	// 重新开始扫码
	setTimeout(startScanning, 300)
}

// 确认打卡
async function confirmCheckin() {
	submitting.value = true
	emit("success", scannedToken.value, latitude.value || null, longitude.value || null)
	// 注意：不在这里关闭弹窗，由父组件处理
}

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
	if (!allowGeolocationTracking.value) {
		return
	}
	
	if (!navigator.geolocation) {
		locationStatus.value = __("Geolocation is not supported by your current browser")
	} else {
		locationStatus.value = __("Locating...")
		navigator.geolocation.getCurrentPosition(
			handleLocationSuccess,
			handleLocationError,
			{
				enableHighAccuracy: true,
				timeout: 10000,
				maximumAge: 0
			}
		)
	}
}

const startScanning = async () => {
	try {
		if (!html5QrCode) {
			html5QrCode = new Html5Qrcode("qr-reader")
		}

		await html5QrCode.start(
			{ facingMode: "environment" }, // 使用后置摄像头
			{
				fps: 10,
				qrbox: { width: 250, height: 250 }
			},
			onScanSuccess,
			onScanError
		)
		
		scanning.value = true
		
		// 检查是否支持手电筒
		checkTorchAvailability()
	} catch (err) {
		console.error("启动扫码失败:", err)
		resultMessage.value = __("Unable to access camera, please check permissions")
		resultMessageClass.value = "text-red-600"
	}
}

const checkTorchAvailability = async () => {
	try {
		// 检查 MediaDevices API 是否支持手电筒
		if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
			const stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: "environment" }
			})
			
			// 检查是否有 torch 约束支持
			const track = stream.getVideoTracks()[0]
			if (track && track.getCapabilities) {
				const capabilities = track.getCapabilities()
				torchAvailable.value = capabilities.torch !== undefined
			}
			
			// 关闭测试流
			stream.getTracks().forEach(track => track.stop())
		}
	} catch (err) {
		// 不支持手电筒或无法检测
		torchAvailable.value = false
	}
}

const toggleTorch = async () => {
	if (!html5QrCode || !scanning.value) {
		return
	}
	
	try {
		const newTorchState = !torchOn.value
		
		// 使用 Html5Qrcode 的 applyVideoConstraints 方法控制手电筒
		await html5QrCode.applyVideoConstraints({
			torch: newTorchState
		})
		
		torchOn.value = newTorchState
	} catch (err) {
		console.error("切换手电筒失败:", err)
		// 如果失败，尝试使用 MediaStreamTrack API
		try {
			const stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: "environment" }
			})
			const track = stream.getVideoTracks()[0]
			if (track && track.applyConstraints) {
				await track.applyConstraints({
					advanced: [{ torch: !torchOn.value }]
				})
				torchOn.value = !torchOn.value
			}
		} catch (e) {
			console.error("手电筒控制失败:", e)
		}
	}
}

const stopScanning = async () => {
	if (html5QrCode && scanning.value) {
		try {
			// 如果手电筒开启，先关闭
			if (torchOn.value) {
				try {
					await html5QrCode.applyVideoConstraints({ torch: false })
					torchOn.value = false
				} catch (e) {
					// 忽略手电筒关闭错误
				}
			}
			
			await html5QrCode.stop()
			scanning.value = false
			torchAvailable.value = false
		} catch (err) {
			console.error("停止扫码失败:", err)
		}
	}
}

const onScanSuccess = async (decodedText) => {
	// 扫到一次就停止
	await stopScanning()
	
	resultMessage.value = __("Verifying...")
	resultMessageClass.value = "text-blue-600"
	
	// 如果启用了地理位置追踪但还没有获取到位置，等待获取完成
	if (allowGeolocationTracking.value && (!latitude.value || !longitude.value)) {
		resultMessage.value = __("Getting location...")
		try {
			await new Promise((resolve, reject) => {
				if (!navigator.geolocation) {
					reject(new Error(__("Geolocation is not supported by your browser")))
					return
				}
				
				navigator.geolocation.getCurrentPosition(
					(position) => {
						handleLocationSuccess(position)
						resolve(position)
					},
					(error) => {
						handleLocationError(error)
						reject(error)
					},
					{
						enableHighAccuracy: true,
						timeout: 10000,
						maximumAge: 0
					}
				)
			})
		} catch (geoError) {
			// 获取位置失败，仍然传递 null，让父组件处理错误
			resultMessage.value = __("Location unavailable, but continuing...")
		}
	}
	
	// 解析 token 获取地点信息
	let locationName = ""
	try {
		const parts = decodedText.split("|")
		if (parts.length >= 1) {
			locationName = parts[0]
		}
	} catch (e) {
		// ignore
	}
	
	// 从后端获取地点描述
	if (locationName) {
		try {
			const response = await fetch(`/api/method/hrms.api.qr_attendance.get_location_info?location_name=${encodeURIComponent(locationName)}`)
			const data = await response.json()
			if (data.message && data.message.description) {
				scannedLocation.value = data.message.description
			} else {
				scannedLocation.value = locationName
			}
		} catch (e) {
			scannedLocation.value = locationName
		}
	} else {
		scannedLocation.value = __("Unknown Location")
	}
	
	// 保存 token，进入确认步骤
	scannedToken.value = decodedText
	resultMessage.value = ""
	
	// 开始更新时间显示
	updateTimeDisplay()
	timeUpdateInterval = setInterval(updateTimeDisplay, 1000)
	
	// 显示确认界面
	confirmStep.value = true
}

const onScanError = (error) => {
	// 扫描错误可以忽略，等待下一帧
}

const resetState = () => {
	// 重置所有状态
	latitude.value = null
	longitude.value = null
	locationStatus.value = ""
	confirmStep.value = false
	scannedToken.value = ""
	scannedLocation.value = ""
	submitting.value = false
	resultMessage.value = ""
	if (timeUpdateInterval) {
		clearInterval(timeUpdateInterval)
		timeUpdateInterval = null
	}
}

const closeModal = async () => {
	await stopScanning()
	resetState()
	emit("close")
}

const handleDismiss = async () => {
	await stopScanning()
	resetState()
	emit("close")
}

watch(() => props.isOpen, async (newVal) => {
	if (newVal) {
		resetState()
		// 如果启用了地理位置追踪，先获取位置
		if (allowGeolocationTracking.value) {
			fetchLocation()
		}
		// 延迟启动，等待 DOM 渲染
		setTimeout(startScanning, 300)
	} else {
		await stopScanning()
		resetState()
	}
})

onBeforeUnmount(async () => {
	await stopScanning()
	if (html5QrCode) {
		html5QrCode.clear()
	}
	if (timeUpdateInterval) {
		clearInterval(timeUpdateInterval)
	}
})

// 暴露 submitting 状态给父组件
defineExpose({
	submitting
})
</script>

