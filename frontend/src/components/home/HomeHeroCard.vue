<template>
	<div class="hero-card">
		<div class="hero-text">
			<h2 class="hero-title">{{ greeting }}{{ employeeName ? `，${employeeName}` : "" }} 👋</h2>
			<div class="hero-meta">
				<span>{{ dateLabel }}</span>
				<span v-if="weatherText">{{ weatherText }}</span>
				<span v-if="summary" class="hero-status">{{ summary }}</span>
			</div>
		</div>

		<button
			v-if="cta"
			type="button"
			class="hero-cta"
			:class="{ 'is-checkout': cta.action === 'OUT' }"
			@click="$emit('scan')"
		>
			<div class="hero-cta-icon">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M3 7V5a2 2 0 0 1 2-2h2" />
					<path d="M17 3h2a2 2 0 0 1 2 2v2" />
					<path d="M21 17v2a2 2 0 0 1-2 2h-2" />
					<path d="M7 21H5a2 2 0 0 1-2-2v-2" />
					<path d="M7 12h10" />
					<path d="M12 7v10" />
				</svg>
			</div>
			<div class="hero-cta-copy">
				<div class="hero-cta-title">{{ cta.title }}</div>
				<div class="hero-cta-description">{{ cta.description }}</div>
			</div>
			<svg class="hero-cta-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M9 18l6-6-6-6" />
			</svg>
		</button>
	</div>
</template>

<script setup>
defineProps({
	employeeName: { type: String, default: "" },
	greeting: { type: String, required: true },
	dateLabel: { type: String, required: true },
	weatherText: { type: String, default: "" },
	summary: { type: String, default: null },
	cta: { type: Object, default: null },
})

defineEmits(["scan"])
</script>

<style scoped>
.hero-card {
	display: flex;
	flex-direction: column;
	gap: 14px;
	min-height: 180px;
	border-radius: 18px;
	background: #ffffff;
	padding: 18px;
	box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 8px 20px rgba(15, 23, 42, 0.03);
}

.hero-title {
	margin: 0;
	font-size: 20px;
	line-height: 1.3;
	font-weight: 800;
	color: #0f172a;
}

.hero-meta {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: wrap;
	margin-top: 8px;
	font-size: 13px;
	font-weight: 500;
	color: #64748b;
}

.hero-status {
	display: inline-flex;
	align-items: center;
	max-width: 100%;
	border-radius: 999px;
	background: #ecfdf5;
	padding: 3px 10px;
	font-size: 12px;
	font-weight: 700;
	color: #065f46;
}

.hero-cta {
	display: flex;
	align-items: center;
	gap: 14px;
	width: 100%;
	margin-top: auto;
	border: 0;
	border-radius: 14px;
	padding: 16px 18px;
	color: #ffffff;
	background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 52%, #3b82f6 100%);
	box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
	transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.hero-cta.is-checkout {
	background: linear-gradient(135deg, #059669 0%, #10b981 52%, #34d399 100%);
	box-shadow: 0 10px 24px rgba(16, 185, 129, 0.22);
}

.hero-cta:active {
	transform: scale(0.98);
	box-shadow: 0 6px 16px rgba(15, 23, 42, 0.16);
}

.hero-cta-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 44px;
	width: 44px;
	height: 44px;
	border-radius: 12px;
	background: rgba(255, 255, 255, 0.18);
}

.hero-cta-icon svg {
	width: 24px;
	height: 24px;
}

.hero-cta-copy {
	flex: 1;
	min-width: 0;
	text-align: left;
}

.hero-cta-title {
	font-size: 16px;
	font-weight: 800;
}

.hero-cta-description {
	margin-top: 3px;
	font-size: 12px;
	font-weight: 500;
	color: rgba(255, 255, 255, 0.82);
}

.hero-cta-arrow {
	width: 18px;
	height: 18px;
	opacity: 0.7;
}
</style>
