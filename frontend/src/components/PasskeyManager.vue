<template>
	<div class="passkey-manager">
		<div class="passkey-card">
			<div class="passkey-header">
				<div class="passkey-icon">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6">
						<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
					</svg>
				</div>
				<div class="passkey-title-section">
					<h3 class="passkey-title">{{ __('NFC Passkey') }}</h3>
					<p class="passkey-subtitle">{{ __('Register for NFC check-in with FaceID/Fingerprint') }}</p>
				</div>
			</div>

			<!-- 已注册状态 -->
			<div v-if="isRegistered" class="passkey-registered">
				<div class="registered-info">
					<div class="registered-badge">
						<svg viewBox="0 0 24 24" fill="none" class="w-5 h-5 text-green-500">
							<path d="M9 12l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							<circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
						</svg>
						<span class="text-green-600 font-medium">{{ __('Registered') }}</span>
					</div>
					<div class="device-info">
						<span class="device-name">{{ deviceName || __('Unknown Device') }}</span>
						<span class="device-date">{{ formatDate(createdAt) }}</span>
					</div>
				</div>
				<button 
					class="delete-btn"
					@click="confirmDelete"
					:disabled="isDeleting"
				>
					<svg v-if="!isDeleting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-4 h-4">
						<path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
					</svg>
					<span v-if="isDeleting" class="loading-spinner"></span>
					<span>{{ isDeleting ? __('Deleting...') : __('Delete') }}</span>
				</button>
			</div>

			<!-- 未注册状态 -->
			<div v-else class="passkey-unregistered">
				<p class="register-hint">
					{{ __('After registration, you can check in by tapping NFC tag and verifying with FaceID/Fingerprint.') }}
				</p>
				<button 
					class="register-btn"
					@click="registerPasskey"
					:disabled="isRegistering"
				>
					<svg v-if="!isRegistering" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-5 h-5">
						<path d="M12 5v14M5 12h14"/>
					</svg>
					<span v-if="isRegistering" class="loading-spinner"></span>
					<span>{{ isRegistering ? __('Registering...') : __('Register Passkey') }}</span>
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { createResource } from 'frappe-ui'
import { IonToast, toastController } from '@ionic/vue'

// State
const isRegistered = ref(false)
const deviceName = ref('')
const createdAt = ref('')
const isRegistering = ref(false)
const isDeleting = ref(false)
const passkeyName = ref('')

// Check if passkey is registered
const checkStatus = createResource({
	url: 'hrms.api.passkey.check_passkey_registered',
	auto: true,
	onSuccess(data) {
		isRegistered.value = data.registered
		deviceName.value = data.device_name || ''
		createdAt.value = data.created_at || ''
	}
})

// Register passkey
async function registerPasskey() {
	if (isRegistering.value) return
	isRegistering.value = true

	try {
		// 动态导入 SimpleWebAuthn
		const { startRegistration } = await import('@simplewebauthn/browser')

		// 1. 获取注册选项
		const optionsRes = await fetch('/api/method/hrms.api.passkey.register_options', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': window.csrf_token || ''
			}
		})
		const optionsData = await optionsRes.json()
		
		if (optionsData.exc) {
			throw new Error(extractError(optionsData.exc))
		}

		const options = optionsData.message

		// 2. 调用 WebAuthn（弹出 FaceID/指纹）
		let credential
		try {
			credential = await startRegistration(options)
		} catch (authErr) {
			if (authErr.name === 'NotAllowedError') {
				throw new Error(__('Registration was cancelled or timed out'))
			}
			throw authErr
		}

		// 3. 发送到后端保存
		const saveRes = await fetch('/api/method/hrms.api.passkey.register_complete', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': window.csrf_token || ''
			},
			body: JSON.stringify({
				credential: JSON.stringify(credential),
				device_name: getDeviceName()
			})
		})
		const result = await saveRes.json()

		if (result.exc) {
			throw new Error(extractError(result.exc))
		}

		// 成功
		await showToast(__('Passkey registered successfully!'), 'success')
		checkStatus.reload()

	} catch (err) {
		console.error('Passkey registration error:', err)
		await showToast(err.message || __('Registration failed'), 'danger')
	} finally {
		isRegistering.value = false
	}
}

// Delete passkey
async function confirmDelete() {
	if (!confirm(__('Are you sure you want to delete this Passkey? You will need to register again to use NFC check-in.'))) {
		return
	}

	isDeleting.value = true

	try {
		// 获取 passkey 列表并删除
		const listRes = await fetch('/api/method/hrms.api.passkey.get_my_passkeys', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': window.csrf_token || ''
			}
		})
		const listData = await listRes.json()
		
		if (listData.message && listData.message.length > 0) {
			const passkey = listData.message[0]
			
			const deleteRes = await fetch('/api/method/hrms.api.passkey.delete_passkey', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': window.csrf_token || ''
				},
				body: JSON.stringify({ passkey_name: passkey.name })
			})
			const deleteData = await deleteRes.json()

			if (deleteData.exc) {
				throw new Error(extractError(deleteData.exc))
			}

			await showToast(__('Passkey deleted'), 'success')
			isRegistered.value = false
			deviceName.value = ''
			createdAt.value = ''
		}
	} catch (err) {
		console.error('Passkey deletion error:', err)
		await showToast(err.message || __('Deletion failed'), 'danger')
	} finally {
		isDeleting.value = false
	}
}

// Helpers
function formatDate(dateStr) {
	if (!dateStr) return ''
	const date = new Date(dateStr)
	return date.toLocaleDateString()
}

function getDeviceName() {
	const ua = navigator.userAgent
	if (/iPhone/i.test(ua)) return 'iPhone'
	if (/iPad/i.test(ua)) return 'iPad'
	if (/Android/i.test(ua)) {
		if (/Samsung/i.test(ua)) return 'Samsung'
		if (/Pixel/i.test(ua)) return 'Google Pixel'
		if (/Xiaomi|Mi /i.test(ua)) return 'Xiaomi'
		if (/HUAWEI/i.test(ua)) return 'Huawei'
		return 'Android'
	}
	if (/Mac/i.test(ua)) return 'Mac'
	if (/Windows/i.test(ua)) return 'Windows'
	return 'Unknown Device'
}

function extractError(exc) {
	if (typeof exc === 'string') {
		const match = exc.match(/ValidationError:\s*(.+)/)
		if (match) return match[1]
		return exc.split('\n')[0]
	}
	return 'Unknown error'
}

async function showToast(message, color = 'primary') {
	const toast = await toastController.create({
		message,
		duration: 3000,
		color,
		position: 'top'
	})
	await toast.present()
}

// i18n helper
function __(text) {
	return window.__ ? window.__(text) : text
}

onMounted(() => {
	checkStatus.reload()
})
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
	align-items: center;
	justify-content: space-between;
	padding: 12px;
	background: #f0fdf4;
	border-radius: 8px;
	gap: 12px;
}

.registered-info {
	flex: 1;
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
