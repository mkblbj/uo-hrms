import test from "node:test"
import assert from "node:assert/strict"
import { getChatUnreadMeta, createChatUnreadRefresher } from "./chatUnread.js"

test("combines private and group unread counts with localized accessible labels", () => {
	assert.deepEqual(getChatUnreadMeta([{ unread_count: 2, is_direct_message: 1 }, { unread_count: 3, is_direct_message: 0 }], "zh"), {
		count: 5, text: "5", label: "聊天，5 条未读消息",
	})
	assert.equal(getChatUnreadMeta([], "ja").text, "")
	assert.equal(getChatUnreadMeta([{ unread_count: 101 }], "en").text, "99+")
	assert.equal(getChatUnreadMeta([{ unread_count: 2 }], "ja").label, "チャット、未読2件")
})

test("reconciles a read received during an unfinished refresh without publishing stale counts", async () => {
	let finishFirst
	let calls = 0
	const seen = []
	const sync = createChatUnreadRefresher(() => {
		calls += 1
		return calls === 1 ? new Promise(resolve => { finishFirst = resolve }) : Promise.resolve([])
	}, rows => seen.push(getChatUnreadMeta(rows).count))
	const first = sync.refresh()
	sync.refresh()
	finishFirst([{ unread_count: 1 }])
	await first
	assert.equal(calls, 2)
	assert.deepEqual(seen, [0])
})

test("does not publish an old account result after disposal", async () => {
	let finish
	const seen = []
	const sync = createChatUnreadRefresher(() => new Promise(resolve => { finish = resolve }), rows => seen.push(rows))
	const pending = sync.refresh()
	sync.dispose()
	finish([{ unread_count: 7 }])
	await pending
	assert.deepEqual(seen, [])
})
