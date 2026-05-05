<template>
	<div class="wet-mayfly-shell" aria-hidden="true">
		<div class="wet-mayfly-loader">
			<span></span>
			<span></span>
			<span></span>
			<span></span>
		</div>
	</div>
</template>

<!-- Source inspiration: https://uiverse.io/Nawsome/wet-mayfly-23 (MIT License). -->
<style scoped>
.wet-mayfly-shell {
	width: 220px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.wet-mayfly-loader {
	position: relative;
	width: 150px;
	height: 96px;
}

.wet-mayfly-loader::before,
.wet-mayfly-loader::after {
	content: "";
	position: absolute;
	top: 15px;
	width: 72px;
	height: 44px;
	border-radius: 72px 72px 10px 72px;
	background: rgba(125, 211, 252, 0.34);
	box-shadow: inset 0 0 20px rgba(255, 255, 255, 0.26);
	transform-origin: bottom right;
	animation: wet-mayfly-wing 1.4s ease-in-out infinite;
}

.wet-mayfly-loader::before {
	left: 0;
}

.wet-mayfly-loader::after {
	right: 0;
	transform: scaleX(-1);
	animation-name: wet-mayfly-wing-right;
}

.wet-mayfly-loader span {
	position: absolute;
	left: 50%;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	background: #f8fafc;
	transform: translateX(-50%);
	box-shadow: 0 0 18px rgba(255, 255, 255, 0.56);
	animation: wet-mayfly-drop 1.4s ease-in-out infinite;
}

.wet-mayfly-loader span:nth-child(1) {
	top: 32px;
}

.wet-mayfly-loader span:nth-child(2) {
	top: 48px;
	width: 15px;
	height: 15px;
	animation-delay: 0.08s;
}

.wet-mayfly-loader span:nth-child(3) {
	top: 62px;
	width: 12px;
	height: 12px;
	animation-delay: 0.16s;
}

.wet-mayfly-loader span:nth-child(4) {
	top: 75px;
	width: 8px;
	height: 8px;
	animation-delay: 0.24s;
}

@keyframes wet-mayfly-wing {
	0%,
	100% {
		transform: rotate(-12deg);
	}

	50% {
		transform: rotate(18deg) translateY(-8px);
	}
}

@keyframes wet-mayfly-wing-right {
	0%,
	100% {
		transform: scaleX(-1) rotate(-12deg);
	}

	50% {
		transform: scaleX(-1) rotate(18deg) translateY(-8px);
	}
}

@keyframes wet-mayfly-drop {
	0%,
	100% {
		transform: translateX(-50%) translateY(0);
		opacity: 0.65;
	}

	50% {
		transform: translateX(-50%) translateY(-8px);
		opacity: 1;
	}
}
</style>
