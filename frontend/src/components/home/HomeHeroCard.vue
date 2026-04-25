<template>
	<div class="hero-card">
		<div class="hero-text">
			<h2 class="hero-title">{{ greeting }} {{ employeeName }} 👋</h2>
			<p class="hero-date">{{ dateLabel }}</p>
			<p v-if="summary" class="hero-summary">{{ summary }}</p>
		</div>
		<button v-if="cta" type="button" class="hero-cta" @click="$emit('scan')">
			<div>
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
	employeeName: { type: String, required: true },
	greeting: { type: String, required: true },
	dateLabel: { type: String, required: true },
	summary: { type: String, default: null },
	cta: { type: Object, default: null },
})

defineEmits(["scan"])
</script>

<style scoped>
.hero-card {
	background: white;
	border-radius: 1.25rem;
	padding: 1rem;
	box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
	display: flex;
	flex-direction: column;
	gap: 0.9rem;
}

.hero-title {
	font-size: 1.125rem;
	font-weight: 800;
	color: #111827;
}

.hero-date {
	font-size: 0.875rem;
	color: #64748b;
}

.hero-summary {
	font-size: 0.8125rem;
	color: #475569;
}

.hero-cta {
	display: flex;
	align-items: center;
	justify-content: space-between;
	border-radius: 1rem;
	padding: 1rem 1.1rem;
	background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
	color: white;
	box-shadow: 0 12px 22px rgba(37, 99, 235, 0.28);
}

.hero-cta-title {
	font-size: 1rem;
	font-weight: 800;
}

.hero-cta-description {
	margin-top: 0.2rem;
	font-size: 0.75rem;
	opacity: 0.9;
}

.hero-cta-arrow {
	width: 1.25rem;
	height: 1.25rem;
}
</style>
