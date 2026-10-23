// Raven keeps its own light/dark choice, separate from the app's time-based theme.
// It stores "light", "dark" or "system" under this key (same origin as the app,
// so the chat tab can read it), and "system" — also the default — follows the phone.
export const RAVEN_THEME_KEY = "raven-theme"

// Raven's --surface-base in each theme: the background of its top bar.
export const RAVEN_SURFACE = { light: "#ffffff", dark: "#171717" }

export function ravenSurfaceColor({ stored, systemDark }) {
	if (stored === "light" || stored === "dark") return RAVEN_SURFACE[stored]
	return systemDark ? RAVEN_SURFACE.dark : RAVEN_SURFACE.light
}
