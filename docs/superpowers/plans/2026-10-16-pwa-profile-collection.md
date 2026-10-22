# PWA 员工资料收集实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 员工在 PWA 填写自己的联系方式，提交后同步原有员工档案；已完成温刚试用，现按最新授权开放所有在职员工。

**Architecture:** `hrms.api.employee_profile` 提供名单状态、本人资料和受限保存三个接口。个人资料页面复用现有 PWA 框架与独立表单组件；首页、个人页使用同一入口组件。所有资料写入 Employee，使用其原有保存及并发校验。

**Tech Stack:** Frappe Python、Vue 3、Ionic、frappe-ui、原有 Vite 构建。

**Spec:** `docs/superpowers/specs/2026-10-16-pwa-profile-collection-design.md`

## Global Constraints

- 当前功能分支和已有未提交改动继续保留；不改动考勤代码。
- 正式站点全员开关 `pwa_profile_collection_enabled` 为 true，试用名单为空；每次访问仍检查在职状态及有效登录账号。
- 新增接口仅允许本人；不能扩大 Employee 或 User 的通用写权限。
- 七项资料和 modified 之外的提交字段拒绝处理。
- 不添加依赖，不代测试员工填写真实资料。

## Review Focus

- 非试用、访客、离职、停用账号不能通过隐藏入口或直接调用获得权限。
- 修改员工编号、user_id、状态、银行字段等额外参数不能越权写入。
- 员工没有通用 Employee 写权限时仍能提交七项本人资料。
- HR 并发更新后，旧表单必须报版本冲突，不能覆盖更新。
- 新名单和新资源在不同账号及 PWA 缓存下仍正确生效；构建保留原有功能。

### Task 1: 本人资料接口

**Files:** 新建 `hrms/api/employee_profile.py`、`hrms/tests/test_employee_profile_collection.py`。

**Interfaces:** `get_collection_status() -> {enabled}`；`get_my_profile() -> profile`；`save_my_profile(profile: dict | str) -> profile`。profile 只公开身份展示、七项资料、modified。

- [x] 先写并运行失败测试：名单、有效账号、本人更新、拒绝额外字段、必填邮箱、版本冲突与 HR 总表同步。
- [x] 实现三接口：会话解析员工，检查名单；固定字段写入 Employee；邮箱优先更新已使用的公司邮箱，否则个人邮箱。
- [x] 独立测试站点执行并通过所有接口测试。

### Task 2: PWA 填写与成功界面

**Files:** 新建 `frontend/src/utils/profileCollection.js` 及测试、`frontend/src/components/profile/ProfileCollectionForm.vue` 及测试、`frontend/src/components/profile/ProfileCollectionEntry.vue`、`frontend/src/views/ProfileCollection.vue`；修改 `Home.vue`、`Profile.vue`、`router/index.js`。

**Interfaces:** 沿用 Task 1 接口，路由 `/profile/complete`，入口只按服务器 enabled 显示。

- [x] 先写表单字段、校验、提交参数限制及 SSR 展示测试，确认新功能缺失时失败。
- [x] 实现预填、行内错误、提交加载、成功摘要、再次修改及首页／个人页入口；提供中日英文案。
- [x] 运行相关 Node 测试，构建前端，在独立站点用手机宽度验证完整流程和非试用访问。

### Task 3: 审查与单人启用

**Files:** `docs/pwa-profile-collection.md`、原有使用说明。

- [x] 用 gpt-6-luna（medium）只读审查本次变更，修复阻塞问题。
- [x] 初期备份并发布到温刚试用；现已按最新授权开启全体在职员工，清空试用名单并清理缓存。
- [x] 正式站点逐一核验全部账号：符合在职及有效账号条件的员工可读取本人资料，其余账号被拒绝，HR 总表角色不变。
- [x] 清理临时测试账号、数据及测试服务器，交付测试入口与验证结果。

后续开放：用户已授权所有在职员工使用，增加显式全员开关；关闭时保留原名单试用模式。HR 全员总表权限不变，不修改员工真实联系资料。
