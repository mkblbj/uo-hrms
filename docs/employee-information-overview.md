# 员工信息总表

入口：Desk 首页的「员工信息总表」快捷图标，或 HR Setup（人力资源工作区）的同名入口。直接地址为 `/desk/query-report/Employee%20Information%20Overview`。

Desk 快捷图标仅向具备 HR／管理员角色及 Employee 报表权限的账号显示，点击直达总表；报表本身继续执行原有角色及资料权限校验。

总表直接读取 Employee 员工档案，默认筛选在职员工；清空状态筛选可查看所有状态。没有账号和资料不完整的员工同样可以展示。HR User、HR Manager、Administrator 可使用；System Manager 还须具备既有 Employee 读取／报表权限。既有公司及员工数据权限继续生效，导出同时检查 Employee 的导出权限。

## 使用

- 按姓名、员工编号、工号、手机号或微信号搜索；公司、部门、状态可以组合筛选，表格和筛选均不显示支店。
- 「未填写电话」「未填写住址」会匹配 NULL、空字符串及纯空白内容；微信号为选填。
- 有 Employee 修改权限时，姓名旁显示「编辑」：可在弹窗中直接修改手机号、微信号、现住址、公司邮箱、个人邮箱，以及紧急联系人姓名、亲属和紧急联系电话。登录账号邮箱只读，保存后总表自动刷新。保存沿用员工档案的权限、格式校验和版本冲突检查，导出仍是原始资料。
- 点击姓名或员工编号打开原有员工档案。在「地址与联系方式」中修改手机号、微信号或现住址，保存后刷新报表。
- 点击手机号或微信号复制；点击现住址查看全文，并可复制完整地址。
- 桌面端固定姓名和员工编号；窄屏固定姓名，横向滑动查看其他列。
- 使用报表右上角菜单的「导出」选择 Excel。导出全部匹配结果，保留电话和工号的前导零、微信号和完整多行地址。邮箱列位于电话之前，优先使用公司邮箱、其次个人邮箱，再以关联登录账号的邮箱补充。

## 安装与升级

新安装通过 `hrms.setup.get_custom_fields` 创建可选文本字段 `Employee.custom_wechat_id`。正常升级通过 `hrms.patches.v16_0.add_employee_wechat_id` 创建该字段，报表及工作区由标准迁移同步。

如当前站点还有其他待处理改动，可在完成发布确认后只同步本功能，避免执行无关迁移：

```python
import frappe
from hrms.patches.v16_0.add_employee_wechat_id import execute

execute()
frappe.reload_doc("hr", "report", "employee_information_overview", force=True)
frappe.reload_doc("hr", "workspace", "hr_setup", force=True)
frappe.clear_cache()
frappe.db.commit()
```

工作区同步会使用仓库中的 HR Setup 定义。已有站点个性化布局时，应保留布局并手动添加报表入口。

## 验证

后端：`hrms.hr.report.employee_information_overview.test_employee_information_overview`，连接独立测试站点后由 unittest 或 bench 测试运行器执行。测试需要标准 `_Test Company`，每项测试创建独立的 26 名模拟员工并回滚。

前端：`node --test hrms/hr/report/employee_information_overview/employee_information_overview.test.cjs`。

测试覆盖全部员工、没有账号、离职状态、搜索和组合筛选、空白资料、角色及数据权限、原生 Excel 导出、姓名跳转、复制、地址全文、安全文本显示与手机固定列。

紧急联系人资料复用员工档案中的姓名、关系和联系电话字段。总表可查看和导出三项，紧急电话可点击复制；「编辑」弹窗中有独立分区可维护这些资料。
