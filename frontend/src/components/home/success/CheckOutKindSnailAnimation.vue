<template>
	<div class="kind-snail-shell" aria-hidden="true">
		<div class="kind-snail-loader">
			<div class="kind-snail-body"></div>
			<div class="kind-snail-head"></div>
			<div class="kind-snail-bubble kind-snail-bubble--one"></div>
			<div class="kind-snail-bubble kind-snail-bubble--two"></div>
		</div>
	</div>
</template>

<!-- Source inspiration: https://uiverse.io/Novaxlo/kind-snail-5 (MIT License). -->
<style scoped>
.kind-snail-shell {
	width: 220px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.kind-snail-loader {
	position: relative;
	width: 162px;
	height: 104px;
}

.kind-snail-body {
	position: absolute;
	left: 28px;
	bottom: 20px;
	width: 94px;
	height: 52px;
	border-radius: 48px 52px 34px 34px;
	background: linear-gradient(180deg, #c49164, #8a5f3c);
	box-shadow: inset 0 -8px 0 rgba(70, 44, 24, 0.18), 0 18px 30px rgba(15, 23, 42, 0.22);
	animation: kind-snail-body 1.8s ease-in-out infinite;
}

.kind-snail-body::before {
	content: "";
	position: absolute;
	left: 18px;
	top: 10px;
	width: 42px;
	height: 25px;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.16);
}

.kind-snail-head {
	position: absolute;
	right: 16px;
	bottom: 36px;
	width: 40px;
	height: 34px;
	border-radius: 22px 20px 18px 18px;
	background: #b98256;
	animation: kind-snail-head 1.8s ease-in-out infinite;
}

.kind-snail-head::before,
.kind-snail-head::after {
	content: "";
	position: absolute;
	top: 8px;
	width: 5px;
	height: 5px;
	border-radius: 50%;
	background: #1f2937;
	box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.38);
}

.kind-snail-head::before {
	left: 9px;
}

.kind-snail-head::after {
	right: 9px;
}

.kind-snail-bubble {
	position: absolute;
	border-radius: 50%;
	background: rgba(255, 255, 255, 0.66);
	animation: kind-snail-bubble 2s ease-in-out infinite;
}

.kind-snail-bubble--one {
	right: 8px;
	top: 15px;
	width: 12px;
	height: 12px;
}

.kind-snail-bubble--two {
	right: 36px;
	top: 2px;
	width: 8px;
	height: 8px;
	animation-delay: 0.35s;
}

@keyframes kind-snail-body {
	0%,
	100% {
		transform: translateX(-4px);
	}

	50% {
		transform: translateX(6px);
	}
}

@keyframes kind-snail-head {
	0%,
	100% {
		transform: translate(0, 0);
	}

	50% {
		transform: translate(7px, -4px);
	}
}

@keyframes kind-snail-bubble {
	0% {
		transform: translateY(12px) scale(0.72);
		opacity: 0;
	}

	40%,
	70% {
		opacity: 0.9;
	}

	100% {
		transform: translateY(-18px) scale(1);
		opacity: 0;
	}
}
</style>
