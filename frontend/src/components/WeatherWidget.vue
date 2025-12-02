<template>
	<div v-if="weather.data" class="weather-row">
		<!-- 今天 -->
		<div class="weather-cell">
			<span class="weather-label">{{ getLabel('today') }}</span>
			<span class="weather-temp">{{ Math.round(weather.data.temp_c) }}°</span>
			<img :src="weather.data.condition.icon" :alt="weather.data.condition.text" class="weather-icon" />
		</div>
		<!-- 分隔线 -->
		<div class="weather-divider"></div>
		<!-- 明天 -->
		<div v-if="forecast.data" class="weather-cell right">
			<span class="weather-label">{{ getLabel('tomorrow') }}</span>
			<span class="weather-temp">{{ Math.round(forecast.data.maxtemp_c) }}°/{{ Math.round(forecast.data.mintemp_c) }}°</span>
			<img :src="forecast.data.condition.icon" :alt="forecast.data.condition.text" class="weather-icon" />
		</div>
	</div>
</template>

<script setup>
import { createResource } from "frappe-ui"
import { inject } from "vue"

const __ = inject("$translate")

const weather = createResource({
	url: "hrms.api.get_weather_data",
	auto: true,
	cache: ["weather_data", 10 * 60 * 1000]
})

const forecast = createResource({
	url: "hrms.api.get_weather_forecast",
	auto: true,
	cache: ["weather_forecast", 30 * 60 * 1000] // 缓存30分钟
})

function getLabel(key) {
	const lang = frappe.boot?.lang || "ja"
	const labels = {
		today: {
			ja: "今日",
			zh: "今天",
			en: "Today"
		},
		tomorrow: {
			ja: "明日",
			zh: "明天",
			en: "Tomorrow"
		}
	}
	return labels[key]?.[lang] || labels[key]?.ja || key
}
</script>

<style scoped>
.weather-row {
	background: white;
	border-radius: 12px;
	padding: 12px 16px;
	display: flex;
	align-items: center;
	box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.weather-cell {
	flex: 1;
	display: flex;
	align-items: center;
	gap: 6px;
}

.weather-cell.right {
	justify-content: flex-end;
}

.weather-divider {
	width: 1px;
	height: 32px;
	background: #e5e7eb;
	margin: 0 16px;
}

.weather-label {
	font-size: 13px;
	font-weight: 500;
	color: #6b7280;
}

.weather-temp {
	font-size: 18px;
	font-weight: 700;
	color: #111827;
}

.weather-icon {
	width: 28px;
	height: 28px;
}
</style>
