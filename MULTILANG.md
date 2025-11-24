# UO HR 多语言支持文档

## 概述
UO HR 系统基于 Frappe Framework 的多语言功能，支持中文、英文和日语。

## 当前支持的语言

### 1. 英语 (English) - 默认语言
- 语言代码: `en`
- 完整支持

### 2. 中文 (简体)
- 语言代码: `zh`
- 来源: Frappe HR 官方翻译
- 文件: `/hrms/locale/zh.po`
- 状态: ✅ 完整支持

### 3. 日语 (Japanese) - 新增
- 语言代码: `ja`
- 来源: 株式会社UO 定制
- 文件: `/hrms/locale/ja.po`
- 状态: 🟡 基础支持（核心术语已翻译）

## 如何启用日语

### 方法 1: 用户级别设置
1. 登录系统
2. 点击右上角用户头像
3. 选择 `Settings` / `设置`
4. 在 `Language` / `语言` 下拉菜单选择 `日本語`
5. 刷新页面

### 方法 2: 系统级别设置
编辑站点配置文件 `site_config.json`:
```json
{
  "lang": "ja"
}
```

### 方法 3: 通过命令行
```bash
# 进入容器
docker-compose exec frappe bash

# 设置用户语言
bench --site hrms.localhost set-config lang ja

# 清除缓存
bench clear-cache
```

## 日语翻译文件说明

### 已翻译的核心术语

#### 人事管理
- 従業員 (Employee)
- 部門 (Department)
- 役職 (Designation)
- 入社日 (Date of Joining)

#### 勤怠管理
- 出勤 (Check In)
- 退勤 (Check Out)
- 遅刻 (Late Entry)
- 早退 (Early Exit)
- 残業 (Overtime)
- 在宅勤務 (Work From Home)

#### 休暇管理
- 年次有給休暇 (Annual Leave)
- 病気休暇 (Sick Leave)
- 産休 (Maternity Leave)
- 育休 (Paternity Leave)
- 代休 (Compensatory Leave)

#### 給与管理
- 基本給 (Basic Salary)
- 手取り額 (Net Pay)
- 住宅手当 (Housing Allowance)
- 交通費 (Transport Allowance)
- 健康保険 (Health Insurance)
- 厚生年金 (Pension)
- 雇用保険 (Employment Insurance)
- 所得税 (Income Tax)

#### 経費精算
- 経費精算 (Expense Claim)
- 出張費 (Travel Expense)
- 食事代 (Meal Expense)
- 宿泊費 (Accommodation)

## 扩展日语翻译

### 1. 手动添加翻译
编辑 `/hrms/locale/ja.po` 文件，按以下格式添加：

```po
msgid "English Text"
msgstr "日本語テキスト"
```

### 2. 使用 Frappe 翻译工具
```bash
# 提取可翻译字符串
bench --site hrms.localhost get-untranslated ja hrms

# 更新翻译文件
bench --site hrms.localhost update-translations
```

### 3. 在线翻译平台
如果需要完整翻译，可以：
1. 导出 `.po` 文件
2. 使用 Poedit 或类似工具编辑
3. 导入回系统

## 翻译优先级

### 高优先级（建议翻译）
- [ ] DocType 标签和字段
- [ ] 报表名称和列标题
- [ ] 工作区和仪表板
- [ ] 错误消息和验证提示
- [ ] 移动端界面文字

### 中优先级
- [ ] 帮助文档
- [ ] 邮件模板
- [ ] 打印格式

### 低优先级
- [ ] 开发者文档
- [ ] 注释和日志消息

## 日本特定功能定制

### 1. 日本假期日历
创建日本假期列表：
```python
# 在 HR Settings 中设置
- 元日 (New Year's Day)
- 成人の日 (Coming of Age Day)
- 建国記念の日 (National Foundation Day)
- 天皇誕生日 (Emperor's Birthday)
- 春分の日 (Vernal Equinox Day)
- 昭和の日 (Showa Day)
- 憲法記念日 (Constitution Memorial Day)
- みどりの日 (Greenery Day)
- こどもの日 (Children's Day)
- 海の日 (Marine Day)
- 山の日 (Mountain Day)
- 敬老の日 (Respect for the Aged Day)
- 秋分の日 (Autumnal Equinox Day)
- 体育の日 (Sports Day)
- 文化の日 (Culture Day)
- 勤労感謝の日 (Labor Thanksgiving Day)
```

### 2. 日本社会保险计算
需要自定义 Salary Component:
- 健康保険 (Health Insurance): ~5%
- 厚生年金 (Pension): ~9.15%
- 雇用保険 (Employment Insurance): ~0.3%
- 所得税 (Income Tax): 累进税率

### 3. 日本工资单格式
创建自定义打印格式，包含：
- 支給 (Earnings)
- 控除 (Deductions)
- 差引支給額 (Net Pay)

## 多语言 UI 组件

### 前端国际化
在 Vue 组件中使用翻译：
```javascript
// 使用 Frappe 的翻译函数
import { __ } from 'frappe-ui'

// 在模板中
<template>
  <div>{{ __('Employee') }}</div>
</template>
```

### 动态翻译
```python
# Python 中
from frappe import _

frappe.msgprint(_("Employee has been created successfully"))
```

## 翻译质量保证

### 测试清单
- [ ] 用户界面显示正确的日语
- [ ] 按钮和菜单项已翻译
- [ ] 错误消息使用日语
- [ ] 邮件通知使用日语
- [ ] 打印格式使用日语
- [ ] 报表列标题使用日语
- [ ] 移动端应用显示日语

### 常见问题

#### Q: 为什么有些文本没有翻译？
A: 可能原因：
1. 该文本未在 `.po` 文件中定义
2. 缓存未清除
3. 文本是硬编码的，未使用翻译函数

解决方法：
```bash
bench clear-cache
bench build --app hrms
```

#### Q: 如何批量翻译所有文本？
A: 
1. 导出完整的 `.pot` 文件
2. 使用专业翻译工具（如 Poedit、Lokalize）
3. 或使用 AI 翻译服务批量处理
4. 人工校对专业术语

#### Q: 混合使用中文和日语可以吗？
A: 可以。每个用户可以单独设置语言偏好。

## 贡献翻译

如果你想改进日语翻译：
1. Fork 项目仓库
2. 编辑 `/hrms/locale/ja.po`
3. 测试翻译
4. 提交 Pull Request

## 翻译资源

### 术语参考
- [日本人事労務用語集](https://www.mhlw.go.jp/)
- 厚生労働省官方术语
- 日本劳动法规标准用语

### 工具推荐
- **Poedit**: GUI 翻译编辑器
- **Lokalize**: KDE 翻译工具
- **DeepL**: 高质量机器翻译
- **Google Translate**: 基础翻译参考

## 技术支持

如需翻译协助，请联系：
- 邮箱: hr@uo.co.jp
- 内部翻译团队

---

© 2025 株式会社UO. All Rights Reserved.

