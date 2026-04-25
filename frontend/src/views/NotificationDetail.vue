<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-screen notification-detail-container">
				<div class="w-full sm:w-96 mx-auto">
					<header
						class="flex flex-row bg-white/80 backdrop-blur-sm shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
					>
						<div class="flex flex-row items-center">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-transparent"
								@click="router.back()"
							>
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</Button>
							<h2 class="text-xl font-semibold text-gray-900">{{ __("通知详情") }}</h2>
						</div>
					</header>

					<div class="p-4" v-if="notification.data">
						<div class="bg-white rounded-xl shadow-sm border p-5">
							<!-- 发送者信息 -->
							<div class="flex items-center gap-3 mb-4 pb-4 border-b">
								<EmployeeAvatar :userID="notification.data.from_user" size="lg" />
								<div class="flex flex-col">
									<span class="font-medium text-gray-900">
										{{ notification.data.from_user_name || notification.data.from_user }}
									</span>
									<span class="text-xs text-gray-500">
										{{ dayjs(notification.data.creation).format('YYYY-MM-DD HH:mm') }}
									</span>
								</div>
							</div>

							<!-- 消息内容 -->
							<div 
								class="notification-content prose prose-sm max-w-none"
								v-html="getDisplayMessage()"
							></div>

							<!-- 关联文档 -->
							<div 
								v-if="notification.data.reference_document_type && notification.data.reference_document_name"
								class="mt-4 pt-4 border-t"
							>
								<Button
									variant="outline"
									class="w-full"
									@click="goToReference"
								>
									<template #prefix>
										<FeatherIcon name="external-link" class="w-4" />
									</template>
									{{ __("查看关联文档") }}
								</Button>
							</div>
						</div>
					</div>

					<div v-else class="p-4">
						<div class="bg-white rounded-xl p-8 text-center text-gray-500">
							{{ __("加载中...") }}
						</div>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonContent, IonPage } from "@ionic/vue"
import { useRouter, useRoute } from "vue-router"
import { createResource, FeatherIcon } from "frappe-ui"
import { inject, onMounted, watch } from "vue"
import EmployeeAvatar from "@/components/EmployeeAvatar.vue"

const dayjs = inject("$dayjs")
const router = useRouter()
const route = useRoute()
const __ = inject("$translate")

const notification = createResource({
	url: "frappe.client.get",
	params: {
		doctype: "PWA Notification",
		name: route.params.id,
	},
	auto: true,
	onSuccess(data) {
		// 标记为已读
		if (data && !data.read) {
			markAsRead()
		}
	}
})

const markAsRead = createResource({
	url: "frappe.client.set_value",
	params: {
		doctype: "PWA Notification",
		name: route.params.id,
		fieldname: "read",
		value: 1
	}
})

function goToReference() {
	const item = notification.data
	if (!item.reference_document_type) return
	
	router.push({
		name: `${item.reference_document_type.replace(/\s+/g, "")}DetailView`,
		params: { id: item.reference_document_name },
	})
}

function getDisplayMessage() {
	const data = notification.data
	if (!data) return ""
	// 如果使用 HTML 源代码模式
	if (data.use_html_source && data.html_source) {
		return data.html_source
	}
	return data.message || ""
}

onMounted(() => {
	if (route.params.id) {
		notification.fetch()
	}
})

watch(() => route.params.id, (newId) => {
	if (newId) {
		notification.params.name = newId
		notification.fetch()
	}
})
</script>

<style scoped>
.notification-detail-container {
	background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.notification-content :deep(img) {
	max-width: 100%;
	border-radius: 8px;
	margin: 12px 0;
}

.notification-content :deep(h1),
.notification-content :deep(h2),
.notification-content :deep(h3) {
	margin-top: 16px;
	margin-bottom: 8px;
	font-weight: 600;
}

.notification-content :deep(p) {
	margin-bottom: 12px;
	line-height: 1.6;
}

.notification-content :deep(a) {
	color: #2563eb;
	text-decoration: underline;
}
</style>

