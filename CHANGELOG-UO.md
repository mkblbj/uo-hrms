# UO HR 变更日志

## [1.0.0-uo] - 2025-11-18

### 新增功能 🎉
- 完成株式会社UO品牌化定制
- 添加中文/日文混合界面支持
- 创建 UO 专属 Logo 和图标系统
- 新增定制化文档（CUSTOMIZATION.md, DEPLOYMENT.md）

### 品牌化改造 🎨
- 应用标题: `Frappe HR` → `UO HR`
- 发布者: `Frappe Technologies` → `株式会社UO`
- 邮箱: `contact@frappe.io` → `hr@uo.co.jp`
- 许可证: `GPL v3` → `Proprietary`
- 所有桌面图标父级更新为 "UO HR"

### Logo 更新 🖼️
- 创建 UO HR 主 Logo (`uo-hr-logo.svg`)
- 更新 PWA Manifest 图标
- 保留原 Frappe HR logo 作为备份

### 配置文件修改 ⚙️
- `hooks.py`: 完整更新应用元信息
- `pyproject.toml`: 更新项目配置和 URL
- `README.md`: 完全重写为 UO 定制版
- `install.py`: 更新安装提示信息
- `uninstall.py`: 更新卸载提示信息

### Desktop 图标更新 📱
更新以下桌面图标的 `parent_icon` 为 "UO HR"：
- frappe_hr.json (主应用图标)
- recruitment.json (招聘)
- employee_lifecycle.json (员工生命周期)
- expense_claims.json (费用报销)
- performance.json (绩效)
- leaves.json (请假)
- attendance.json (考勤)
- tax_&_benefits.json (税务与福利)
- salary_payout.json (薪资发放)

### 文档改进 📚
- 添加 `CUSTOMIZATION.md`: 详细定制说明文档
- 添加 `DEPLOYMENT.md`: 生产环境部署指南
- 更新 `README.md`: 移除 Frappe Cloud，添加 UO 特定内容
- 添加 `CHANGELOG-UO.md`: UO 版本变更记录

### 技术债务 🔧
- 清理所有 `Frappe HR` 文本引用
- 更新错误报告链接到 UO 仓库
- 统一中文/日文提示信息

### 保留功能 ✅
以下核心功能完全保留，无任何修改：
- 员工管理系统
- 考勤和排班
- 请假管理
- 薪资计算和税务
- 绩效考核
- 招聘流程
- 费用报销
- 培训管理
- 员工生命周期管理
- 报表和分析功能

### 依赖关系 📦
- Frappe Framework: >=16.0.0-dev,<17.0.0
- ERPNext: >=16.0.0-dev,<17.0.0
- Python: >=3.10
- Node.js: (通过 Frappe Framework)

### 部署信息 🚀
- 推荐部署方式: Docker Compose
- 支持的操作系统: Ubuntu 20.04/22.04 LTS, Debian 11/12
- 数据库: MariaDB 10.6+ / PostgreSQL 13+
- Web 服务器: Nginx (推荐使用反向代理)

### 安全更新 🔒
- 更改默认联系邮箱为内部邮箱
- 移除公开仓库引用
- 添加安全漏洞报告流程

### 已知问题 ⚠️
- Logo 图片文件 (PNG) 需要手动替换为实际设计的 logo
- 多语言翻译文件 (`locale/`) 保持原状，可根据需要进行本地化
- 某些界面文本可能仍包含英文，需要后续逐步汉化

### 后续计划 📅
- [ ] 添加日本特定的薪资计算规则
- [ ] 集成日本社会保险计算
- [ ] 添加日本假期日历
- [ ] 优化移动端界面（日文/中文）
- [ ] 添加更多自定义报表

### 升级说明 ⬆️
从 Frappe HR 原版升级到 UO 定制版：
1. 备份现有数据
2. 拉取 UO HR 代码
3. 执行 `bench migrate`
4. 清除缓存: `bench clear-cache`
5. 重新构建资源: `bench build --app hrms`

### 贡献者 👥
- UO 开发团队

### 许可证变更 📄
本定制版本为株式会社UO专有软件。
基于 Frappe HR (GPL v3) 进行定制开发。

---

## 基础版本信息
本定制版基于 **Frappe HR v16.0.0-dev** 进行开发。

原始项目: https://github.com/frappe/hrms
原始许可: GNU General Public License v3.0

---

© 2025 株式会社UO. All Rights Reserved.

