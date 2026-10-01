<template>
	<div class="passkey-manager">
		<div class="passkey-card">
			<div class="passkey-header">
				<div class="passkey-icon">
					<Icon icon="lucide-scan-face" class="w-6 h-6" />
				</div>
				<div class="passkey-title-section">
					<h3 class="passkey-title">{{ __("Face ID / Fingerprint Check-in") }}</h3>
					<p class="passkey-subtitle">
						{{ __("Check in by just glancing at your phone. Set up once per phone.") }}
					</p>
				</div>
			</div>

			<div v-if="devices.length" class="passkey-registered">
				<div v-for="device in devices" :key="device.name" class="registered-info">
					<div class="device-info">
						<span class="device-name">{{ device.device_name || __("Unknown Device") }}</span>
						<span class="device-date">
							{{ formatDate(device.created_at) }}
							<template v-if="device.last_used">
								· {{ __("Last used") }} {{ formatDate(device.last_used) }}
							</template>
						</span>
					</div>
					<button
						class="delete-btn"
						:disabled="deletingName === device.name"
						@click="removeDevice(device)"
					>
						<span v-if="deletingName === device.name" class="loading-spinner"></span>
						<span>{{ __("Remove") }}</span>
					</button>
				</div>
			</div>
			<p v-else class="register-hint">{{ __("No devices set up yet") }}</p>

			<button
				v-if="devices.length < MAX_DEVICES"
				class="register-btn"
				:disabled="isRegistering"
				@click="registerPasskey"
			>
				<span v-if="isRegistering" class="loading-spinner"></span>
				<span>{{ __("Set Up This Phone") }}</span>
			</button>
			<p v-else class="register-hint">{{ __("Up to {0} devices", [MAX_DEVICES]) }}</p>
		</div>
	</div>
</template>

<script setup>
import { inject, onMounted, ref } from "vue"
import { Icon } from "frappe-ui"
import { toastController } from "@ionic/vue"

import { createFrappeCaller } from "@/utils/passkeyCheckin"

const __ = inject("$translate")
const MAX_DEVICES = 3
const devices = ref([])
const isRegistering = ref(false)
const deletingName = ref("")
const call = createFrappeCaller({
	fetchImpl: (...args) => fetch(...args),
	getCsrfToken: () => window.csrf_token || "",
})

async function loadDevices() {
	try {
		devices.value = (await call("hrms.api.passkey.get_my_passkeys", {})) || []
	} catch (_) {
		devices.value = []
	}
}

async function registerPasskey() {
	if (isRegistering.value) return
	isRegistering.value = true
	try {
		const { startRegistration } = await import("@simplewebauthn/browser")
		const options = await call("hrms.api.passkey.register_options", {})
		let credential
		try {
			credential = await startRegistration({ optionsJSON: options })
		} catch (authErr) {
			if (authErr.name === "NotAllowedError") {
				throw new Error(__("Registration was cancelled or timed out"))
			}
			throw authErr
		}
		await call("hrms.api.passkey.register_complete", {
			credential: JSON.stringify(credential),
			device_name: getDeviceName(),
		})
		await showToast(__("Passkey registered successfully!"), "success")
		await loadDevices()
	} catch (err) {
		console.error("Passkey registration error:", err)
		await showToast(err.message || __("Registration failed"), "danger")
	} finally {
		isRegistering.value = false
	}
}

async function removeDevice(device) {
	if (!confirm(__("Remove this device? It will no longer be able to check in with Face ID / fingerprint."))) {
		return
	}
	deletingName.value = device.name
	try {
		await call("hrms.api.passkey.delete_passkey", { passkey_name: device.name })
		await showToast(__("Passkey deleted"), "success")
		await loadDevices()
	} catch (err) {
		console.error("Passkey deletion error:", err)
		await showToast(err.message || __("Deletion failed"), "danger")
	} finally {
		deletingName.value = ""
	}
}

function formatDate(dateStr) {
	if (!dateStr) return ""
	return new Date(dateStr).toLocaleDateString()
}

function getDeviceName() {
	const ua = navigator.userAgent
	if (/iPhone/i.test(ua)) return "iPhone"
	if (/iPad/i.test(ua)) return "iPad"
	if (/Android/i.test(ua)) {
		if (/Samsung/i.test(ua)) return "Samsung"
		if (/Pixel/i.test(ua)) return "Google Pixel"
		if (/Xiaomi|Mi /i.test(ua)) return "Xiaomi"
		if (/HUAWEI/i.test(ua)) return "Huawei"
		return "Android"
	}
	if (/Mac/i.test(ua)) return "Mac"
	if (/Windows/i.test(ua)) return "Windows"
	return "Unknown Device"
}

async function showToast(message, color = "primary") {
	const toast = await toastController.create({
		message,
		duration: 3000,
		color,
		position: "top",
	})
	await toast.present()
}

onMounted(loadDevices)
</script>

<style scoped>
.passkey-manager {
	padding: 0;
}

.passkey-card {
	background: white;
	border-radius: 12px;
	padding: 16px;
	box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.passkey-header {
	display: flex;
	align-items: flex-start;
	gap: 12px;
	margin-bottom: 16px;
}

.passkey-icon {
	width: 40px;
	height: 40px;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

.passkey-icon svg {
	color: white;
}

.passkey-title-section {
	flex: 1;
}

.passkey-title {
	font-size: 16px;
	font-weight: 600;
	color: #1f2937;
	margin: 0 0 2px 0;
}

.passkey-subtitle {
	font-size: 13px;
	color: #6b7280;
	margin: 0;
}

/* 已注册状态 */
.passkey-registered {
	display: flex;
	flex-direction: column;
	gap: 8px;
	margin-bottom: 12px;
}

.registered-info {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	padding: 12px;
	background: #f0fdf4;
	border-radius: 8px;
}

.registered-badge {
	display: flex;
	align-items: center;
	gap: 6px;
	margin-bottom: 4px;
}

.device-info {
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.device-name {
	font-size: 14px;
	color: #374151;
	font-weight: 500;
}

.device-date {
	font-size: 12px;
	color: #9ca3af;
}

.delete-btn {
	display: flex;
	align-items: center;
	gap: 6px;
	padding: 8px 12px;
	background: white;
	border: 1px solid #fecaca;
	border-radius: 6px;
	color: #dc2626;
	font-size: 13px;
	cursor: pointer;
	transition: all 0.2s;
}

.delete-btn:hover:not(:disabled) {
	background: #fef2f2;
}

.delete-btn:disabled {
	opacity: 0.6;
	cursor: not-allowed;
}

/* 未注册状态 */
.passkey-unregistered {
	text-align: center;
}

.register-hint {
	font-size: 13px;
	color: #6b7280;
	margin-bottom: 16px;
	line-height: 1.5;
}

.register-btn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	padding: 12px 24px;
	background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
	color: white;
	border: none;
	border-radius: 10px;
	font-size: 15px;
	font-weight: 600;
	cursor: pointer;
	transition: all 0.2s;
	width: 100%;
}

.register-btn:hover:not(:disabled) {
	transform: translateY(-1px);
	box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.register-btn:disabled {
	opacity: 0.7;
	cursor: not-allowed;
	transform: none;
}

/* Loading spinner */
.loading-spinner {
	width: 16px;
	height: 16px;
	border: 2px solid currentColor;
	border-top-color: transparent;
	border-radius: 50%;
	animation: spin 0.8s linear infinite;
}

@keyframes spin {
	to { transform: rotate(360deg); }
}
</style>
