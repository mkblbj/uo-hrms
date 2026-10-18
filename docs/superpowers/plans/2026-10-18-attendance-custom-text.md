# 员工自定义出勤退勤语句实施计划

> 当前会话按superpowers:executing-plans实施；独立审查使用gpt-6-luna / medium。

**Goal:** 管理员能为每位员工分别输入完整的出勤、退勤朗读语句，试听后仅生成并发布本人。
**Architecture:** 私有草稿增加employee_texts={Employee.name:{IN:text,OUT:text}}，每项空白时使用原姓氏问候；_text统一供试听、生成及本人指纹使用。现有员工行用可展开编辑区容纳两项文本，不新增页面或设备协议。
**Tech Stack:** 既有Frappe/Python、Desk原生JS、VOICEVOX/Nemo及24kHz WAV。
**Spec:** 用户明确要求“继续定制个人，加入可以自定义出勤、退勤语音，自己输入文字”。实施语义已在会话说明：输入完整句、不自动追加称呼，两项各自留空恢复默认。

## Global Constraints

- 两项分别保存，支持普通声音组及个人专属声音；不绑定必须先启用个人音色。
- 每项最多120字单行文字，去除首尾空白；仍为24kHz/PCM16/单声道/5秒/256KiB，超长提示缩短朗读内容。
- 旧草稿无写盘迁移，空employee_texts不改变旧全员或本人待发布指纹。
- 本人文本修改使本人待发布结果失效，其他员工文本修改不影响本人；全员任务保留完整快照检查。
- 生成清单逐段记录实际text；只改语音朗读，原打卡状态、设备v1、QR120秒、天气保持。
- 不自动修改正式员工草稿或发布音频，不覆盖生产其他未提交文件。

## Review Focus

- 完整句不能重复添加姓氏、“さん”或默认问候；IN/OUT独立回退。
- 非字符串、非映射、错误动作、超长/换行/空字节拒绝；离职员工旧配置不阻碍保存。
- 旧任务升级兼容和实际文本指纹；发布仍仅合并本人两段。
- HTML等文本仅作为文字显示，输入保留且搜索/保存重开可用；小屏可展开编辑，不横向溢出。
- 长语句不截断或放宽固件格式，错误提示针对完整朗读内容。

### Task 1: 文本保存与语音链路

Files: hrms/utils/attendance_voice_settings.py、hrms/utils/attendance_voice_engine.py、hrms/tests/test_attendance_voice_settings.py。

- [x] RED：完整句保存/试听、独立默认回退、输入校验/离职清理、本人文本指纹与其他人隔离、生成清单text、旧本人待发布兼容。
- [x] 实现employee_texts规范化和统一_text路由，空表指纹兼容；清单保存text，更新5秒错误提示。
- [x] 设置45、引擎6、CSV准备9、设备19（共79项）回归及Ruff通过，提交。

### Task 2: 中文编辑与上线

Files: hrms/hr/page/attendance_voice_settings/attendance_voice_settings.js、docs/attendance-voice-settings.md及本计划。

- [x] 员工行可展开“自定义出勤/退勤”，独立输入、标签/示例/默认与5秒说明；保存、试听、仅生成本人/发布本人沿用原流程。
- [x] 隔离浏览器/GPU验证不同IN/OUT原句、特殊符号保存重开、OUT空项回退、本人两段生成发布及其他7人映射/文件不变；375px可用。
- [x] gpt-6-luna / medium独立审查无发现；4b81b8178/f391ed873已合入正式，页面200、超长417、访客403及设备回归通过，正式草稿/manifest和48个其他文件SHA一致。
- [x] 恢复测试站点配置、停测试web8015/临时worker并恢复正式引擎服务active，两个QA会话注销，文档记录并交付页面入口。
