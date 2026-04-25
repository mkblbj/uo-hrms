<template>
	<div
		v-if="workStatus.data"
		:class="[
			'px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all duration-300',
			workStatus.data.is_working
				? 'bg-green-100 text-green-700 border border-green-300'
				: 'bg-gray-100 text-gray-600 border border-gray-300'
		]"
	>
		<span
			:class="[
				'w-1.5 h-1.5 rounded-full',
				workStatus.data.is_working ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
			]"
		></span>
		<span>{{ getStatusText() }}</span>
	</div>
	<div v-else-if="workStatus.loading" class="px-2.5 py-1">
		<span class="text-xs text-gray-400">...</span>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui";
import { inject, onMounted, onBeforeUnmount } from "vue";

const __ = inject("$translate");

const workStatus = createResource({
	url: "hrms.api.get_employee_work_status",
	auto: true,
	cache: false, // 不缓存，每次都获取最新状态
});

// 每30秒刷新一次状态
let refreshInterval = null;

// 监听打卡状态变化事件
const handleCheckinStatusChange = (event) => {
	// 打卡成功后立即刷新状态
	workStatus.reload();
};

onMounted(() => {
	// 定时刷新
	refreshInterval = setInterval(() => {
		workStatus.reload();
	}, 30000); // 30秒
	
	// 监听打卡事件
	window.addEventListener('checkin-status-changed', handleCheckinStatusChange);
});

onBeforeUnmount(() => {
	if (refreshInterval) {
		clearInterval(refreshInterval);
	}
	
	// 移除事件监听
	window.removeEventListener('checkin-status-changed', handleCheckinStatusChange);
});

const getStatusText = () => {
	if (!workStatus.data) return "";
	
	// 使用 frappe.boot.lang 获取当前语言设置
	const lang = window.frappe?.boot?.lang || "ja";
	
	if (workStatus.data.is_working) {
		// 正在上班
		if (lang === "ja") return "勤務中";
		if (lang === "zh") return "上班中";
		return "Working";
	} else {
		// 不在上班
		if (lang === "ja") return "退勤済";
		if (lang === "zh") return "已下班";
		return "Off Work";
	}
};
</script>

<style scoped>
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
</style>
