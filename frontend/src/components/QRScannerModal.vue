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
				<h2 class="text-lg font-bold">{{ __("Scan QR Code") }}</h2>
				<button @click="closeModal" class="text-gray-500">
					<FeatherIcon name="x" class="w-6 h-6" />
				</button>
			</div>

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
		</div>
	</ion-modal>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, inject, computed } from "vue"
import { IonModal } from "@ionic/vue"
import { FeatherIcon, Button, createResource } from "frappe-ui"
import { Html5Qrcode } from "html5-qrcode"

const __ = inject("$translate")

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

// 获取 HR Settings
const settings = createResource({
	url: "hrms.api.get_hr_settings",
	auto: true,
})

const allowGeolocationTracking = computed(() => {
	return settings.data?.allow_geolocation_tracking || false
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
	
	// 调用打卡 API，传递地理位置信息
	emit("success", decodedText, latitude.value || null, longitude.value || null)
}

const onScanError = (error) => {
	// 扫描错误可以忽略，等待下一帧
}

const closeModal = async () => {
	await stopScanning()
	// 重置地理位置状态
	latitude.value = null
	longitude.value = null
	locationStatus.value = ""
	emit("close")
}

const handleDismiss = async () => {
	await stopScanning()
	// 重置地理位置状态
	latitude.value = null
	longitude.value = null
	locationStatus.value = ""
	emit("close")
}

watch(() => props.isOpen, async (newVal) => {
	if (newVal) {
		resultMessage.value = ""
		// 如果启用了地理位置追踪，先获取位置
		if (allowGeolocationTracking.value) {
			fetchLocation()
		}
		// 延迟启动，等待 DOM 渲染
		setTimeout(startScanning, 300)
	} else {
		await stopScanning()
		// 重置地理位置状态
		latitude.value = null
		longitude.value = null
		locationStatus.value = ""
	}
})

onBeforeUnmount(async () => {
	await stopScanning()
	if (html5QrCode) {
		html5QrCode.clear()
	}
})
</script>

