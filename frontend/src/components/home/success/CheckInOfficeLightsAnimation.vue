<template>
	<div class="office-lights-shell" aria-hidden="true">
		<div class="office-building">
			<div v-for="index in 9" :key="index" class="office-window"></div>
		</div>
		<div class="office-ground"></div>
	</div>
</template>

<style scoped>
.office-lights-shell {
	position: relative;
	width: 220px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.office-building {
	width: 132px;
	height: 126px;
	padding: 18px;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 11px;
	border-radius: 18px 18px 8px 8px;
	background: linear-gradient(180deg, #1e3a8a 0%, #172554 100%);
	box-shadow: 0 22px 42px rgba(15, 23, 42, 0.34), inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.office-building::before {
	content: "";
	position: absolute;
	width: 52px;
	height: 10px;
	top: 10px;
	left: 50%;
	transform: translateX(-50%);
	border-radius: 8px 8px 0 0;
	background: #0f172a;
}

.office-window {
	border-radius: 7px;
	background: rgba(148, 163, 184, 0.28);
	box-shadow: 0 0 0 rgba(251, 191, 36, 0);
	animation: office-light-on 2.4s ease-in-out infinite;
}

.office-window:nth-child(2n) {
	animation-delay: 0.18s;
}

.office-window:nth-child(3n) {
	animation-delay: 0.36s;
}

.office-window:nth-child(5) {
	animation-delay: 0.52s;
}

.office-ground {
	position: absolute;
	width: 164px;
	height: 9px;
	bottom: 15px;
	border-radius: 999px;
	background: rgba(191, 219, 254, 0.22);
	filter: blur(0.2px);
}

@keyframes office-light-on {
	0%,
	18% {
		background: rgba(148, 163, 184, 0.28);
		box-shadow: 0 0 0 rgba(251, 191, 36, 0);
	}

	36%,
	82% {
		background: #fde68a;
		box-shadow: 0 0 18px rgba(251, 191, 36, 0.8);
	}

	100% {
		background: rgba(148, 163, 184, 0.32);
		box-shadow: 0 0 0 rgba(251, 191, 36, 0);
	}
}
</style>
