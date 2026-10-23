import { reactive } from "vue"
import { createResource } from "frappe-ui"

import { employees } from "./employees"
import { employeeResource } from "./employee"
import { userResource } from "./user"
import { PHOTO_STATUS_METHOD } from "@/utils/profilePhoto"

// 全局头像提醒与首页卡片共用状态；由全局入口在登录后检查。
export const profilePhotoStatus = createResource({ url: PHOTO_STATUS_METHOD })

// 头像提醒弹窗：全局入口每次打开应用时弹出（倒计时后才能跳过），首页卡片也能随时打开（可直接关掉）
export const photoReminder = reactive({ open: false, snoozeDelay: 0 })

export function openPhotoReminder(snoozeDelay = 0) {
	photoReminder.snoozeDelay = snoozeDelay
	photoReminder.open = true
}

// 换了头像后，顶栏、个人页和列表里的头像都要刷新
export function refreshProfilePhoto() {
	userResource.reload()
	employeeResource.reload()
	employees.reload()
}
