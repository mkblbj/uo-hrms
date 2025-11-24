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
- 主 Logo: `/hrms/public/images/uo-hr-logo.svg`
- 公司 Logo: `/hrms/public/images/uo-company-logo.jpg`
- Manifest Logo: `/hrms/public/manifest/frappe-hr-logo.svg` (已更新为 UO 标识)
- Desktop 图标: 所有桌面图标的 `parent_icon` 已更新为 "UO HR"

### 3. 配置文件修改

#### hooks.py
```python
app_title = "UO HR"
app_publisher = "株式会社UO"
app_description = "UO人力资源管理系统"
app_email = "hr@uo.co.jp"
app_logo_url = "/assets/hrms/images/uo-hr-logo.svg"
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

