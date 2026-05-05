<template>
	<div class="curvy-bulldog-shell" aria-hidden="true">
		<div class="curvy-bulldog-loader">
			<span></span>
			<span></span>
			<span></span>
		</div>
	</div>
</template>

<!-- Source inspiration: https://uiverse.io/Shoh2008/curvy-bulldog-27 (MIT License). -->
<style scoped>
.curvy-bulldog-shell {
	width: 220px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.curvy-bulldog-loader {
	position: relative;
	width: 130px;
	height: 80px;
}

.curvy-bulldog-loader::before {
	content: "";
	position: absolute;
	inset: 18px 7px 10px;
	border-radius: 999px 999px 26px 26px;
	background: linear-gradient(135deg, #f8fafc, #cbd5e1);
	box-shadow: 0 18px 32px rgba(15, 23, 42, 0.28);
	animation: curvy-bulldog-body 1.8s ease-in-out infinite;
}

.curvy-bulldog-loader::after {
	content: "";
	position: absolute;
	right: 0;
	top: 22px;
	width: 42px;
	height: 36px;
	border-radius: 20px 22px 16px 18px;
	background: #f8fafc;
	box-shadow: inset -7px -5px 0 #cbd5e1, -72px 2px 0 -10px #f8fafc;
	animation: curvy-bulldog-head 1.8s ease-in-out infinite;
}

.curvy-bulldog-loader span {
	position: absolute;
	bottom: 0;
	width: 13px;
	height: 28px;
	border-radius: 999px;
	background: #e2e8f0;
	transform-origin: top center;
	animation: curvy-bulldog-step 0.9s ease-in-out infinite;
}

.curvy-bulldog-loader span:nth-child(1) {
	left: 28px;
}

.curvy-bulldog-loader span:nth-child(2) {
	left: 58px;
	animation-delay: -0.45s;
}

.curvy-bulldog-loader span:nth-child(3) {
	left: 88px;
}

@keyframes curvy-bulldog-body {
	0%,
	100% {
		transform: translateY(0) rotate(-2deg);
	}

	50% {
		transform: translateY(-8px) rotate(2deg);
	}
}

@keyframes curvy-bulldog-head {
	0%,
	100% {
		transform: translate(0, 0);
	}

	50% {
		transform: translate(4px, -5px);
	}
}

@keyframes curvy-bulldog-step {
	0%,
	100% {
		transform: rotate(-10deg) translateY(0);
	}

	50% {
		transform: rotate(12deg) translateY(6px);
	}
}
</style>
