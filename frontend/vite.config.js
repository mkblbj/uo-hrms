import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import { VitePWA } from "vite-plugin-pwa"
import frappeui from "frappe-ui/vite"

import path from "path"
import fs from "fs"

const packageJson = JSON.parse(fs.readFileSync(new URL("./package.json", import.meta.url), "utf8"))
const frontendBuildTime = process.env.HRMS_FRONTEND_BUILD_TIME || new Date().toISOString()
const frontendVersion =
	process.env.HRMS_FRONTEND_VERSION || `${packageJson.version}-${frontendBuildTime}`

export default defineConfig({
	server: {
		port: 8080,
		proxy: getProxyOptions(),
		allowedHosts: true,
	},
	define: {
		__HRMS_FRONTEND_VERSION__: JSON.stringify(frontendVersion),
		__HRMS_FRONTEND_BUILD_TIME__: JSON.stringify(frontendBuildTime),
	},
	plugins: [
		vue(),
		frappeui(),
		emitFrontendVersionPlugin({
			version: frontendVersion,
			buildTime: frontendBuildTime,
		}),
		VitePWA({
			registerType: "autoUpdate",
			strategies: "injectManifest",
			injectRegister: null,
			devOptions: {
				enabled: true,
			},
			manifest: {
				display: "standalone",
				name: "UO HR",
				short_name: "UO HR",
				start_url: "/hrms",
				description: "株式会社UO人力资源管理系统",
				theme_color: "#1E40AF",
				icons: [
					{
						src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
						sizes: "192x192",
						type: "image/png",
						purpose: "any",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
						sizes: "192x192",
						type: "image/png",
						purpose: "maskable",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
						sizes: "512x512",
						type: "image/png",
						purpose: "any",
					},
					{
						src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
						sizes: "512x512",
						type: "image/png",
						purpose: "maskable",
					},
				],
			},
		}),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "../hrms/public/frontend",
		emptyOutDir: true,
		target: "es2015",
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
		sourcemap: true,
		rollupOptions: {
			output: {
				manualChunks: {
					"frappe-ui": ["frappe-ui"],
				},
			},
		},
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "showdown", "tailwind.config.js", "engine.io-client"],
	},
})

function emitFrontendVersionPlugin({ version, buildTime }) {
	return {
		name: "hrms-frontend-version",
		apply: "build",
		generateBundle() {
			this.emitFile({
				type: "asset",
				fileName: "frontend-version.json",
				source: JSON.stringify({ version, buildTime }, null, "\t"),
			})
		},
	}
}

function getProxyOptions() {
	const config = getCommonSiteConfig()
	const webserver_port = config ? config.webserver_port : 8000
	if (!config) {
		console.log("No common_site_config.json found, using default port 8000")
	}
	return {
		"^/(app|login|api|assets|files|private)": {
			target: `http://127.0.0.1:${webserver_port}`,
			ws: true,
			router: function (req) {
				const site_name = req.headers.host.split(":")[0]
				console.log(`Proxying ${req.url} to ${site_name}:${webserver_port}`)
				return `http://${site_name}:${webserver_port}`
			},
		},
	}
}

function getCommonSiteConfig() {
	let currentDir = path.resolve(".")
	// traverse up till we find frappe-bench with sites directory
	while (currentDir !== "/") {
		if (
			fs.existsSync(path.join(currentDir, "sites")) &&
			fs.existsSync(path.join(currentDir, "apps"))
		) {
			let configPath = path.join(currentDir, "sites", "common_site_config.json")
			if (fs.existsSync(configPath)) {
				return JSON.parse(fs.readFileSync(configPath))
			}
			return null
		}
		currentDir = path.resolve(currentDir, "..")
	}
	return null
}
