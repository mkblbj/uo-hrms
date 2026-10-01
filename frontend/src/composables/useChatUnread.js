import { computed, onBeforeUnmount, ref, watch } from "vue"
import { call } from "frappe-ui"
import { createChatUnreadRefresher, getChatUnreadMeta } from "@/utils/chatUnread"

export function useChatUnread(socket, enabled, user, lang) {
	const rows = ref([])
	let sync = null
	let timer = null

	function refresh() {
		clearTimeout(timer)
		if (!enabled.value || !sync) return
		timer = setTimeout(() => {
			sync?.refresh().catch(error => console.warn("Could not refresh chat unread count", error))
		}, 150)
	}

	function connect() {
		if (enabled.value) socket.emit("doctype_subscribe", "Raven User")
		refresh()
	}

	function visible() {
		if (document.visibilityState === "visible") refresh()
	}

	watch([enabled, () => user.data?.name], () => {
		sync?.dispose()
		clearTimeout(timer)
		rows.value = []
		sync = enabled.value ? createChatUnreadRefresher(
			() => call("raven.api.raven_message.get_unread_count_for_channels"),
			counts => { rows.value = counts },
		) : null
		if (socket.connected) {
			socket.emit(enabled.value ? "doctype_subscribe" : "doctype_unsubscribe", "Raven User")
		}
		refresh()
	}, { immediate: true })

	socket.on("raven:unread_channel_count_updated", refresh)
	socket.on("connect", connect)
	window.addEventListener("focus", refresh)
	document.addEventListener("visibilitychange", visible)
	onBeforeUnmount(() => {
		sync?.dispose()
		clearTimeout(timer)
		socket.off("raven:unread_channel_count_updated", refresh)
		socket.off("connect", connect)
		if (enabled.value) socket.emit("doctype_unsubscribe", "Raven User")
		window.removeEventListener("focus", refresh)
		document.removeEventListener("visibilitychange", visible)
	})

	return computed(() => getChatUnreadMeta(rows.value, lang.value))
}
