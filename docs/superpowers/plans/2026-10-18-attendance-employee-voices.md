# 员工专属考勤声音实施计划

> **For agentic workers:** 使用superpowers:executing-plans在当前会话实施；完成后以gpt-6-luna / medium独立代码审查。

**Goal:** 管理员可以为指定员工独立选择VOICEVOX/Nemo声音、语速、音高和抑扬，试听后沿用生成及手动发布流程。

**Architecture:** 私有草稿新增employee_voices覆盖表，优先于手动声音组与性别组；不启用专属时继续使用既有分组。现有中文Desk页面复用声音编辑区，员工行增加专属选择和编辑入口；正式设备仍只下载已发布WAV。

**Tech Stack:** 既有Frappe/Python、Desk原生JS、VOICEVOX/Nemo引擎、24kHz PCM16音频。

**Spec:** 本会话用户“对于某些员工可以定制专属音声，请帮我优化一下”，已明确选择“单独选择和调整VOICEVOX音色”。支持独立角色/风格、语速、音高和抑扬，保留现有固定签到签退问候与姓氏假名。

## Global Constraints

- 正式员工资料、草稿内容及已发布manifest保持原值；上线功能不自动启用任何员工专属声音或发布新音频。
- 不改变男女/默认配置、原读音、设备API、二维码120秒、天气或24kHz/PCM16/单声道/5秒/256KiB规范。
- 保留旧草稿和已有待发布任务的可用性；空的employee_voices不影响旧fingerprint。
- 只改本功能文件；生产有其他任务未提交代码，禁止覆盖。GPU优先及空闲关闭仍用现有引擎管理机制。
- 管理权限沿用HR Manager / System Manager。

## Review Focus

- 专属配置优先于手动组与性别；清除专属后正确回到所选声音组。
- 同组员工使用不同专属音色时，生成清单不得互相覆盖参数或丢失任何实际音声署名。
- 旧草稿无需写盘迁移；新增空配置不让原待发布音频错误失效。
- 编辑员工声音、切换组和切换员工不能把参数写到另一个对象；保存后重开、搜索及窄屏操作可用。
- 改变专属配置后旧任务不可发布，试听和保存不替换正式语音。

### Task 1: 私有配置、路由和生成

Files: 修改hrms/utils/attendance_voice_settings.py；修改hrms/tests/test_attendance_voice_settings.py。

Interfaces: draft.employee_voices为{Employee.name: {engine,speaker_id,speed,intonation,pitch?}}，pitch默认0、页面范围-0.15～0.15，服务端拒绝超界和非有限值；get_settings始终提供该表；_voice_for(config,employee)优先使用有效专属配置；manifest.source.employee_voices逐人记录实际参数、voice和credit，普通组保留在source.profiles。引擎render追加可选pitch参数，透传pitchScale；旧配置缺失pitch时不新增字段，保留旧fingerprint。

- [x] 写失败测试：专属保存及IN/OUT试听优先级；清除专属回组且同事不受影响；非法配置拒绝及离职员工清理；同组多专属署名；专属修改使旧任务失效；旧待发布任务和文件保持；音高保存及引擎实际请求字段。
- [x] 隔离站点运行hrms.tests.test_attendance_voice_settings及test_attendance_voice_engine，确认新行为缺失导致失败。
- [x] 实现employee_voices校验、旧配置扩展、优先路由、空表fingerprint兼容及生成元数据，以及可选音高透传，不新增端点。
- [x] 同模块GREEN；相邻engine、prepare及设备API模块回归，Ruff通过。
- [x] 提交服务与测试：2c06f16f2。

### Task 2: 中文界面、验证和部署

Files: 修改hrms/hr/page/attendance_voice_settings/attendance_voice_settings.js、docs/attendance-voice-settings.md及本计划。

Interfaces: 复用Task1的employee_voices及既有管理API；员工行选择“专属声音”时复制该员工当前有效组配置，顶端编辑器切到该员工；退出专属时删除对应覆盖表项。

- [x] 在员工行增加专属选项和编辑入口，顶端选择器列出已启用专属的员工，明确当前编辑对象；继续使用既有角色/风格、语速、抑扬和试听播放器，补充音高控制。
- [x] 保存、重开、生成及发布沿用原流程；保留选择、输入和未保存提示，控件具备可读标签，移动端无水平溢出。
- [x] 隔离站点真实浏览器验证两名员工不同专属声音、试听路由、恢复分组、切换不串值、保存重开、生成及发布；用已有GPU引擎验证实际24k输出。
- [x] 按gpt-6-luna / medium做一次独立代码审查；无发现。
- [x] 快进合入正式HRMS并reload-doc/clear-cache；核对正式页面及只读设备回归，旧文件/草稿/manifest哈希相同；停止临时web/引擎worker并恢复正式服务。
- [x] 文档同步使用步骤和实际验证结果，向用户交付正式页面入口。

## 最终验证

功能提交2c06f16f2，页面提交d9b46fee9；66项相关测试及Ruff/Prettier/JS语法通过。gpt-6-luna / medium独立审查无发现。隔离浏览器真实GPU走通两员工不同角色和音高、切换/恢复/保存重开、9人18段生成与手动发布，12个文件全部规格和SHA有效；375px无水平溢出。

正式公网页面脚本包含专属与音高控件；28名员工可配置、未自动启用。以临时参数试听返回青山龍星24kHz单声道PCM16，未保存草稿或改发布状态；访客设置与试听下载403。QR120秒、events200、旧正式WAV200及SHA通过；原48个文件、草稿及manifest哈希一致。隔离配置与正式引擎租约服务恢复，两个QA会话注销。
