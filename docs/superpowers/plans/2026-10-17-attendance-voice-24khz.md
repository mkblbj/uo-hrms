# 考勤语音统一 24 kHz 实施计划

> 使用 superpowers:executing-plans 在当前隔离工作区直接实施；最终审查使用 gpt-6-luna / medium。

**Goal:** 试听、网页批量生成、CSV生成和发布校验统一使用24kHz原始音质，交付本机固件调整说明。
**Architecture:** 保持设备接口v1、PCM16单声道与5秒上限；统一采样率常量24000，完整WAV最多262144字节，PCM最多120000帧。采样率加入草稿生成指纹，禁止把升级前的待发布资源当作新24k资源发布。
**Tech Stack:** 当前Frappe/Python、VOICEVOX/Nemo、现有GPU按需服务。
**Spec:** 用户明确要求统一24kHz，服务端先完成，再交付本机调整说明；沿用现有管理员手动发布流程。

## Global Constraints

- 不修改原有未提交工作；现有员工读音、音色、语速保持。
- 不把16k旧文件升采样伪装成24k，所有新资源由引擎直接生成。
- 正式旧音频保持可下载，用户在本机升级和试听后单独发布新资源；不自动切换正式声音。
- 服务端新生成/导入只接收24kHz、PCM16、单声道、最长5秒；保护旧manifest的原子发布语义不变。

## Review Focus

5秒24k文件超过旧192000字节上限；小于字节上限但超过5秒必须拒绝；旧待发布生成需失效；旧正式16k资源在迁移期间仍可读；固件必须按WAV头配置真实播放率并同步缓冲上限。

### Task 1: 格式升级与回归

Files: hrms/utils/attendance_sign_audio.py, attendance_sign_prepare.py, attendance_voice_engine.py, attendance_voice_settings.py；对应4个既有测试模块。
- [x] 更新真实WAV夹具与引擎HTTP边界预期为24k；新增精确5秒通过、超1帧/旧16k/截断拒绝、旧生成指纹不可发布测试；先观察RED。
- [x] 共享24000常量、262144字节及120000帧上限；两个合成入口使用24k；生成指纹和来源元数据纳入采样率；运行相关完整测试。

### Task 2: 上线与交接

Files: docs/attendance-sign-{design,local,local-connection,server,validation}.md, docs/attendance-voice-settings.md；新增docs/attendance-sign-24khz-firmware-handoff.md。
- [x] 当前操作文档和管理页说明同步24k，历史16k验证记录明确标注历史。
- [x] 写可转发给本机Codex的说明：接口不变、24k/PCM16/mono、5秒/256KiB、WAV解析、I2S/ES8311、旧16k过渡、提示音、缓存和实机验收。
- [ ] 最终独立审查和必要修正，限定文件提交并部署；正式GPU试听24k/无降采样、设备旧资源可读、设置和正式manifest未被覆盖。
- [ ] 提供24k虚构测试WAV和SHA256及可转发说明，最终报告服务端/本机分工。
