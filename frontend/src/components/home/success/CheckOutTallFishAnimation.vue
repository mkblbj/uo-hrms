<template>
	<div class="tall-fish-shell" aria-hidden="true">
		<div class="tall-fish-loader">
			<span></span>
			<span></span>
			<span></span>
		</div>
	</div>
</template>

<!-- Source inspiration: https://uiverse.io/Pradeepsaranbishnoi/tall-fish-38 (MIT License). -->
<style scoped>
.tall-fish-shell {
	width: 220px;
	height: 160px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.tall-fish-loader {
	position: relative;
	width: 150px;
	height: 150px;
	perspective: 220px;
}

.tall-fish-loader span {
	position: absolute;
	top: 50%;
	left: 50%;
	border-radius: 50%;
	border-style: outset;
	background: transparent;
	transform-origin: 50% 50%;
	animation: tall-fish-orbit 1.1s cubic-bezier(0.49, 0.06, 0.43, 0.85) infinite;
}

.tall-fish-loader span:nth-child(1) {
	width: 112px;
	height: 112px;
	margin: -56px 0 0 -56px;
	border-width: 30px;
	border-color: #1e3f57;
}

.tall-fish-loader span:nth-child(2) {
	width: 132px;
	height: 132px;
	margin: -66px 0 0 -66px;
	border-width: 22px;
	border-color: #447891;
	animation-delay: 75ms;
}

.tall-fish-loader span:nth-child(3) {
	width: 150px;
	height: 150px;
	margin: -75px 0 0 -75px;
	border-width: 15px;
	border-color: #6bb2cd;
	animation-delay: 150ms;
}

@keyframes tall-fish-orbit {
	0% {
		filter: brightness(1);
		transform: rotateX(24deg) rotateY(20deg) rotateZ(0deg) translateZ(-25px);
	}

	50% {
		filter: brightness(1.18);
		transform: rotateX(20deg) rotateY(20deg) rotateZ(50deg) translateZ(0);
	}

	100% {
		filter: brightness(1);
		transform: rotateX(24deg) rotateY(20deg) rotateZ(0deg) translateZ(-25px);
	}
}
</style>
