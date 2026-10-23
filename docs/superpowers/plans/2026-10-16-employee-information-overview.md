# 员工信息总表实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 让 HR／管理员在后台集中查询、补齐和导出所有员工的联系资料。

**Architecture:** 以 Employee 为唯一资料来源，新增 Employee Information Overview Script Report。微信字段由安装配置和升级补丁维护；通过 HR Setup 工作区进入报表。使用原有权限查询、员工档案和 Excel 导出。

**Tech Stack:** Frappe、Python、原生 JavaScript、frappe-datatable。

**Spec:** `docs/superpowers/specs/2026-10-16-employee-information-overview-design.md`

## Global Constraints

- 保留当前工作区已有的考勤改动；实现工作在当前功能分支完成。
- 不新增前端依赖；不创建第二份员工资料。
- 不擅自修改员工真实联系方式，默认筛选在职，清空状态可查看全部员工；不按有无账号排除员工。
- 实际数据库验证使用独立的 attendance-sign-test.localhost 测试站点。
- 本次完成代码与测试；运行站点的启用通过定向同步完成，避免执行其他待处理迁移。

## Review Focus

- 普通员工、Guest 或只有其他管理角色的用户不能查询或导出总表。
- 超过默认分页数、没有账号和离职的员工仍出现在结果中。
- 空字符串、NULL、纯空白的电话／地址能被缺失筛选识别，微信缺失不影响完整度。
- 地址与姓名包含 HTML 特殊字符时按纯文本显示；电话、微信号和地址复制原文。
- 既有用户数据权限继续生效，Excel 保留前导零、完整地址和全部筛选结果。

### Task 1: 微信字段与受权限约束的员工查询

**Files:** `hrms/setup.py`、`hrms/patches.txt`、`hrms/patches/v16_0/add_employee_wechat_id.py`、`hrms/hr/report/employee_information_overview/{__init__.py,employee_information_overview.py,employee_information_overview.json,test_employee_information_overview.py}`。

**Interfaces:** 新字段 `Employee.custom_wechat_id: Data`；报表 `execute(filters=None) -> (columns, data)`。

- [x] 先写测试，验证微信可选、角色拒绝、全员覆盖、搜索、组合筛选及缺失筛选；运行并确认因功能缺失而失败。
- [x] 添加字段安装配置与幂等升级补丁，创建报表权限定义。
- [x] 实现 `execute`：先校验 HR／管理员角色，再用有权限约束的 Employee 查询获取全部行；仅接受已定义筛选，按姓名和编号稳定排序。
- [x] 在独立测试站点应用新字段，运行数据库集成测试，确认全部通过。

### Task 2: 表格交互与工作区入口

**Files:** `hrms/hr/report/employee_information_overview/{employee_information_overview.js,employee_information_overview.test.cjs}`、`hrms/hr/workspace/hr_setup/hr_setup.json`、`hrms/translations/{zh,ja}.csv`。

**Interfaces:** 注册 `frappe.query_reports["Employee Information Overview"]`；沿用 Task 1 的字段与筛选名。

- [x] 先写前端行为测试，验证档案链接、空值、原文复制、长地址展示、转义与固定列；确认功能缺失时失败。
- [x] 实现原生报表筛选、姓名档案链接、联系方式复制及地址查看；不改变服务器返回的原始数据，确保导出正确。
- [x] 在 HR Setup 增加报表快捷方式、导航和关键报表入口，添加中日文翻译。
- [x] 执行 Node 测试，检查 JSON 与 JavaScript 语法，在浏览器验证桌面及手机宽度。

### Task 3: 导出与交付验证

**Files:** 同报表集成测试、`docs/employee-information-overview.md`。

**Interfaces:** 复用 `frappe.desk.query_report.run` 和 `export_query`。

- [x] 测试真实报表请求与 Excel 导出：全员数量、组合筛选、原始文本与未授权访问。
- [x] 记录入口、更新资料方法和定向启用步骤。
- [x] 运行最终相关测试和格式检查；按用户要求由 gpt-6-luna、medium 进行一次代码审查，修复阻塞问题。
- [x] 核对最终 diff，仅保留本功能改动；报告结果与实际验证范围。
