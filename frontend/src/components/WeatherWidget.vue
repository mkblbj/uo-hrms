<template>
	<div v-if="weather.data" class="weather-simple">
		<div class="weather-column">
			<div class="weather-item today">
				<div class="weather-header">
					<span class="weather-label">{{ getLabel('today') }}</span>
					<img :src="weather.data.condition.icon" :alt="weather.data.condition.text" class="weather-icon-small" />
				</div>
				<div class="weather-info">
					<div class="temp-range">
						<span class="weather-temp">{{ Math.round(weather.data.temp_c) }}°C</span>
						<span v-if="weather.data.maxtemp_c && weather.data.mintemp_c" class="temp-minmax">
							{{ Math.round(weather.data.maxtemp_c) }}° / {{ Math.round(weather.data.mintemp_c) }}°
						</span>
					</div>
					<span class="weather-desc">{{ weather.data.condition.text }}</span>
				</div>
			</div>
			<div v-if="forecast.data" class="weather-item tomorrow">
				<div class="weather-header">
					<span class="weather-label">{{ getLabel('tomorrow') }}</span>
					<img :src="forecast.data.condition.icon" :alt="forecast.data.condition.text" class="weather-icon-small" />
				</div>
				<div class="weather-info">
					<div class="temp-range">
						<span class="weather-temp">{{ Math.round(forecast.data.maxtemp_c) }}° / {{ Math.round(forecast.data.mintemp_c) }}°</span>
					</div>
					<span class="weather-desc">{{ forecast.data.condition.text }}</span>
				</div>
			</div>
		</div>
	</div>
	<div v-else-if="weather.loading" class="weather-simple loading">
		<span class="loading-text">{{ __("Loading weather...") }}</span>
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
.weather-simple {
	background: white;
	border-radius: 10px;
	padding: 12px;
	box-shadow: 0 2px 6px rgba(0,0,0,0.05);
	border: 1px solid #e5e7eb;
}

.weather-simple.loading {
	display: flex;
	align-items: center;
	justify-content: center;
	min-height: 70px;
}

.loading-text {
	color: #9ca3af;
	font-size: 13px;
}

.weather-column {
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.weather-item {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.weather-item.tomorrow {
	padding-top: 10px;
	border-top: 1px solid #e5e7eb;
}

.weather-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.weather-label {
	font-size: 11px;
	font-weight: 600;
	color: #6b7280;
	text-transform: uppercase;
	letter-spacing: 0.5px;
}

.weather-icon-small {
	width: 32px;
	height: 32px;
	flex-shrink: 0;
}

.weather-info {
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.temp-range {
	display: flex;
	align-items: baseline;
	gap: 8px;
}

.weather-temp {
	font-size: 20px;
	font-weight: 700;
	color: #111827;
}

.temp-minmax {
	font-size: 14px;
	font-weight: 500;
	color: #9ca3af;
}

.weather-desc {
	font-size: 13px;
	color: #6b7280;
}
</style>
