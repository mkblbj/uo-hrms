# UO HR 系统定制说明

## 概述
本系统基于开源项目 [Frappe HR](https://github.com/frappe/hrms) 进行二次开发，专为株式会社UO定制。

## 定制内容

### 1. 品牌信息修改
- **应用名称**: Frappe HR → UO HR
- **发布者**: Frappe Technologies → 株式会社UO
- **邮箱**: contact@frappe.io → hr@uo.co.jp
- **许可证**: GPL v3 → Proprietary（专有）
- **仓库地址**: https://github.com/uo/hrms

### 2. Logo 和图标
- 主 Logo: `/hrms/public/images/uo-hr-attendance-logo.png`
- 公司 Logo: `/hrms/public/images/uo-company-logo.jpg`
- PWA 图标: `/hrms/public/manifest/manifest-icon-192.png`、`manifest-icon-512.png` 及对应的 maskable 图标
- iOS 图标和启动画面: `/hrms/public/manifest/apple-icon-180.png`、`apple-splash-*.jpg`
- Desktop 图标: 所有桌面图标的 `parent_icon` 已更新为 "UO HR"

### 3. 配置文件修改

#### hooks.py
```python
app_title = "UO HR"
app_publisher = "株式会社UO"
app_description = "UO人力资源管理系统"
app_email = "hr@uo.co.jp"
app_logo_url = "/assets/hrms/images/uo-hr-attendance-logo.png"
```

#### pyproject.toml
```toml
[project]
name = "hrms"
authors = [{ name = "株式会社UO", email = "hr@uo.co.jp" }]
description = "UO人力资源管理系统"

[project.urls]
Homepage = "https://uo.co.jp/hr"
Repository = "https://github.com/uo/hrms.git"
```

### 4. 安装/卸载脚本
- `install.py`: 更新为 "UO HR System" 提示信息
- `uninstall.py`: 更新为 "UO HR" 提示信息

### 5. 文档更新
- `README.md`: 完全重写为 UO 定制版本
- 移除 Frappe Cloud 相关内容
- 添加日本劳动法规合规说明
- 更新安装和部署指南

## 保留的原始功能

以下核心功能完全保留：
- 员工生命周期管理
- 考勤和排班系统
- 请假管理
- 薪资和税务管理
- 绩效考核
- 招聘管理
- 费用报销
- 培训管理

## 技术架构

### 后端
- **Frappe Framework**: Python/JavaScript 全栈框架
- **ERPNext**: 依赖的 ERP 核心模块
- **数据库**: MariaDB/PostgreSQL

### 前端
- **Frappe UI**: Vue.js 组件库
- **响应式设计**: 支持移动端访问

## 开发指南

### 本地开发环境
```bash
cd /home/uo/dev/hrms/docker
docker-compose up
```

### 重新构建资源
```bash
bench build --app hrms
```

### 清除缓存
```bash
bench --site hrms.localhost clear-cache
bench --site hrms.localhost clear-website-cache
```

### 数据库迁移
```bash
bench --site hrms.localhost migrate
```

## 定制模块位置

### 自定义字段
- 路径: `/hrms/hr/doctype/[doctype_name]/`
- 通过 Frappe UI 或代码添加

### 自定义报表
- 路径: `/hrms/hr/report/[report_name]/`
- 支持 Python 查询或 SQL 查询

### 自定义脚本
- 客户端脚本: `/hrms/public/js/`
- 服务端脚本: `/hrms/hr/doctype/[doctype_name]/[doctype_name].py`

### 自定义工作区
- 路径: `/hrms/hr/workspace/`
- JSON 格式配置文件

## 打卡

两种打卡方式共用同一套规则（`hrms/api/checkin_service.py`）：冷却规则、建记录、审计日志、推送墙上屏。记录上的 `checkin_method` 字段标明打卡方式。

- **面容/指纹一键打卡**（PWA 首页，`hrms/api/passkey.py` 的 `get_checkin_context` / `begin_checkin` / `complete_checkin`）：通行密钥核对本人，公司网络或手机定位（打卡点关联的 Shift Location 半径内）证明在场，证据不足时转去扫码。HR 设置「面容/指纹打卡」里设打卡点、对全员开启或试用名单。
- **扫码**（`hrms/api/qr_attendance.py`）：墙上屏动态二维码；打卡点可勾选「要求展示密钥」，勾选前先用表单上的「复制墙上屏网址」更新墙上设备。
- **NFC 打卡已停用**（2026-09-29）：`/nfc_checkin` 只显示停用提示，原来的访客接口 `auth_options` / `passkey_checkin` 已删除；历史记录的 `checkin_method` 仍是 `NFC Passkey`，通行密钥继续用于面容打卡。

在场与定位（`hrms/api/checkin_location.py`）：
- 连着公司网络就算在公司，扫码和面容打卡都不再要手机定位；即使手机另外送了偏远的坐标，也不按距离拦（Employee Checkin 的距离检查同样放行）。
- 不在公司网络、且开着「地理位置追踪」时要定位：扫码缺坐标时 `qr_checkin` 返回 `{"status": "need_location"}`，PWA 定位后再交一次；有坐标就按打卡点半径查距离。
- 位置只在打卡那一刻核对：已保存的打卡记录，HR 事后改别的字段（坐标没动）时不再按定位规则拦；改了坐标才重新核对。
- PWA 取定位（`frontend/src/utils/checkinLocation.js`）：总共最多等约 8 秒。先要普通精度、可用半分钟内的位置；误差超过 100 米且还剩 1.5 秒以上，才用剩下的时间（最多 5 秒）精确定位一次。拿不到时按原因（被拒绝 / 超时或拿不到 / 不支持）给出做法，扫码确认页有「重新获取」，面容打卡面板有「再试一次」和扫码。
- 定位失败会记一条 Error Log，标题 `Checkin Location Failure - <原因>`，内容只有流程（qr / passkey）、等了多久和机型，不记位置；只记员工账号，每人每小时最多 20 条。机型里的 iOS 版本取自浏览器标识，新版 iOS 可能固定报 18.x，只作参考。

安全相关：
- 通行密钥用 py_webauthn 核对（`hrms/api/passkey_webauthn.py`），锁定 `webauthn==2.8.0` 以兼容 Frappe 锁定的 cryptography / pyOpenSSL 版本；RP 默认 `erphr.toiroworld.com`，可用站点配置 `passkey_rp_id`、`passkey_origins` 覆盖（开发站点用 localhost）。
- 真实客户端地址取 `CF-Connecting-IP`（`hrms/utils/client_network.py`），前提是源站只经 Cloudflare 隧道对外；HR 设置「公司网络」每行一个 IP 或网段，支持 IPv6 前缀。
- 员工角色对 `Employee Checkin` 只有读权限；打卡记录的新建、改时间、删除只允许受信接口（`flags.trusted_checkin_source`）或 HR 角色（控制器守卫）。

## 备份与恢复

### 备份站点
```bash
bench --site hrms.localhost backup --with-files
```

### 恢复站点
```bash
bench --site hrms.localhost restore [backup_file]
```

## 安全注意事项

1. **敏感信息保护**
   - 员工个人信息加密存储
   - 薪资数据访问权限严格控制
   - 定期备份数据

2. **权限管理**
   - 遵循最小权限原则
   - 定期审查用户权限
   - 使用角色基础访问控制（RBAC）

3. **漏洞报告**
   - 联系: security@uo.co.jp
   - 响应时间: 24小时内

## 技术支持

### 内部支持
- 邮箱: hr@uo.co.jp
- 内网文档: 参考公司内网文档中心

### 上游项目
- Frappe Framework: https://frappeframework.com/docs
- Frappe HR: https://docs.frappe.io/hr

## 版本历史

### v1.0.0-uo (2025-11-18)
- 基于 Frappe HR v16.0.0-dev 进行定制
- 完成品牌化改造
- 更新所有配置文件
- 添加日文/中文支持

## 许可证

本定制版本为株式会社UO专有软件，未经授权不得使用、复制或分发。

原始 Frappe HR 项目采用 GNU GPL v3 许可证。

---

© 2025 株式会社UO. All Rights Reserved.
