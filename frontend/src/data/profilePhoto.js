import { createResource } from "frappe-ui"

import { employees } from "./employees"
import { employeeResource } from "./employee"
import { userResource } from "./user"
import { PHOTO_STATUS_METHOD } from "@/utils/profilePhoto"

// 全局强制弹窗与首页卡片共用状态；由全局入口在登录后检查。
export const profilePhotoStatus = createResource({ url: PHOTO_STATUS_METHOD })

// 换了头像后，顶栏、个人页和列表里的头像都要刷新
export function refreshProfilePhoto() {
	userResource.reload()
	employeeResource.reload()
	employees.reload()
}
