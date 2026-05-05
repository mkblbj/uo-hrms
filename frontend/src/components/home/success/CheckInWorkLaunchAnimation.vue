<template>
	<div class="work-launch-shell" aria-hidden="true">
		<div class="work-launch-card">
			<div class="work-launch-header">
				<span></span>
				<span></span>
				<span></span>
			</div>
			<div class="work-launch-lines">
				<span></span>
				<span></span>
				<span></span>
			</div>
			<div class="work-launch-bar">
				<div class="work-launch-bar__fill"></div>
				<div class="work-launch-bar__shine"></div>
			</div>
		</div>
	</div>
</template>

<style scoped>
.work-launch-shell {
	width: 230px;
	height: 150px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.work-launch-card {
	position: relative;
	width: 196px;
	height: 112px;
	padding: 14px;
	border-radius: 18px;
	background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(30, 64, 175, 0.82));
	box-shadow: 0 24px 46px rgba(15, 23, 42, 0.32), inset 0 0 0 1px rgba(255, 255, 255, 0.1);
	overflow: hidden;
}

.work-launch-header {
	display: flex;
	gap: 6px;
}

.work-launch-header span {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: rgba(191, 219, 254, 0.66);
}

.work-launch-lines {
	display: grid;
	gap: 8px;
	margin-top: 18px;
}

.work-launch-lines span {
	height: 7px;
	border-radius: 999px;
	background: rgba(226, 232, 240, 0.18);
}

.work-launch-lines span:nth-child(1) {
	width: 74%;
}

.work-launch-lines span:nth-child(2) {
	width: 54%;
}

.work-launch-lines span:nth-child(3) {
	width: 64%;
}

.work-launch-bar {
	position: absolute;
	left: 14px;
	right: 14px;
	bottom: 14px;
	height: 18px;
	border-radius: 999px;
	background: rgba(15, 23, 42, 0.42);
	overflow: hidden;
}

.work-launch-bar__fill {
	width: 0;
	height: 100%;
	border-radius: inherit;
	background: linear-gradient(90deg, #38bdf8, #22c55e, #facc15);
	animation: work-launch-fill 2.2s ease-in-out infinite;
}

.work-launch-bar__shine {
	position: absolute;
	inset: 0;
	background: linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.34) 38%, transparent 68%);
	transform: translateX(-100%);
	animation: work-launch-shine 2.2s ease-in-out infinite;
}

@keyframes work-launch-fill {
	0% {
		width: 0;
	}

	68%,
	88% {
		width: 100%;
	}

	100% {
		width: 0;
	}
}

@keyframes work-launch-shine {
	0%,
	26% {
		transform: translateX(-100%);
	}

	70%,
	100% {
		transform: translateX(100%);
	}
}
</style>
