export function getChatUnreadMeta(rows = [], lang = "zh") {
	const count = rows.reduce((total, row) => total + Number(row.unread_count), 0)
	const labels = {
		zh: count ? `聊天，${count} 条未读消息` : "聊天",
		ja: count ? `チャット、未読${count}件` : "チャット",
		en: count ? `Chat, ${count} unread messages` : "Chat",
	}
	return { count, text: count ? (count > 99 ? "99+" : String(count)) : "", label: labels[lang] || labels.zh }
}

export function createChatUnreadRefresher(fetchCounts, onCounts) {
	let active = true
	let pending = false
	let running = null

	function refresh() {
		if (!active) return Promise.resolve()
		pending = true
		if (running) return running
		running = (async () => {
			try {
				while (active && pending) {
					pending = false
					const rows = await fetchCounts()
					if (active && !pending) onCounts(rows)
				}
			} finally {
				running = null
			}
		})()
		return running
	}

	return { refresh, dispose() { active = false } }
}
