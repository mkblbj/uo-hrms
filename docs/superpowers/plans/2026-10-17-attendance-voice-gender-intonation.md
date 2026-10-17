# 男女分组音色与抑扬调整实施计划

> 使用 superpowers:executing-plans，当前会话实施；独立审查gpt-6-luna / medium。

**Goal:** 男、女员工各自设置引擎/角色/风格/语速/抑扬，按员工性别默认路由并允许手动覆盖，试听及批量生成遵守同样选择。
**Architecture:** 保留原顶层声音作为其他/未填写性别的默认配置；新增profiles.male/female独立声音配置及voice_groups员工覆盖表，旧设置无损继承。员工gender进入快照及指纹；所有声源参数传入同一24k GPU合成路径。
**Tech Stack:** 现有Frappe Desk Page、私有JSON、VOICEVOX/Nemo。
**Spec:** 用户要求男女声音独立调整，并增加抑扬。用户已明确两者都需要：默认自动分组，亦可逐员工手动指定男/女/默认声音组；覆盖只影响语音，不修改员工资料。

## Global Constraints

保留姓氏读音、24k/PCM16/mono/5秒/256KiB、管理员权限及独立发布；不改变员工资料或现有正式声音。两组初始继承原音色，不替用户挑声音。其他性别/未填沿用原默认，页面可调整默认组。抑扬范围0～2，默认1，语速仍0.5～2。

## Review Focus

旧草稿无损迁移；0抑扬保留；NaN/inf/越界拒绝；按员工性别而非当前编辑组选声音；员工性别变更阻止旧资源发布；混合声音发布清单保留各组署名；切换组不丢编辑、音色目录不串组。

### Task 1: 服务与参数

Files: hrms/utils/attendance_voice_settings.py, attendance_voice_engine.py；对应test_attendance_voice_settings.py/test_attendance_voice_engine.py。
- [ ] RED: 旧设置迁移不写磁盘、男女/其他路由、独立参数保存、抑扬0及非法值、性别改变阻止发布、混合来源元数据、真实HTTP边界intonationScale。
- [ ] 实现voice参数规范化、旧格式迁移、gender读取、按员工选配置、参数下传和来源快照；相关43项基线及新增测试GREEN。

### Task 2: 中文页面与上线

Files: hrms/hr/page/attendance_voice_settings/attendance_voice_settings.js, docs/attendance-voice-settings.md。
- [ ] 设置组切换（男/女/默认）、独立声音控件、抑扬slider+数字及含义、员工表标当前声音组；保持现有试听/生成/发布。
- [ ] 隔离浏览器验证切换保留参数、按行试听正确组、24k音频、窄屏；真实GPU不同抑扬合成；最终review并限定文件部署。
- [ ] 正式只读及试听验证，保存的原草稿和manifest保持不变，用户自行设置并生成发布。
