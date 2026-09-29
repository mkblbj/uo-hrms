import { employees } from "./employees"
import { employeeResource } from "./employee"
import { userResource } from "./user"

// 换了头像后，顶栏、个人页和列表里的头像都要刷新
export function refreshProfilePhoto() {
	userResource.reload()
	employeeResource.reload()
	employees.reload()
}
