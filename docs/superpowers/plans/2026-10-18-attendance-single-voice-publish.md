# 单员工语音生成和发布实施计划

> 使用superpowers:executing-plans在当前会话实施；完成后按用户要求由gpt-6-luna / medium审查。

**Goal:** 修改一位员工后仅生成和发布该员工的签到、签退两段语音，保留其他员工的正式声音。
**Architecture:** start_generation(revision,employee_id=None)增加可选员工；沿用单个后台任务槽，针对本人有效参数、文本及姓名检查是否过期。发布时在现有锁内读取最新正式清单，原子合并本人两段映射；其他员工文件及映射不变。全员模式保持原逻辑。
**Tech Stack:** 现有Frappe/Python、Desk JS、私有WAV及GPU优先的VOICEVOX服务。
**Spec:** 本会话用户明确要求“只生成和发布这个员工的语音”。固定IN/OUT问候、24k规范、设备v1及原读音/音色编辑流程保持。

## Global Constraints

- 不自动改正式员工草稿或发布音频；功能部署与实际发布由管理员分别操作。
- 单员工任务只合成两段；发布保留其他员工音频字节与映射，兼容其他员工仍为旧16k的正式资源。
- 保留原男女/默认/专属路由、参数校验、管理权限、陈旧结果拒绝及原子清单替换。
- 当前仍一次一个任务，单员工与全员共用状态；旧无employee_id任务按全员处理。
- 不覆盖生产其他任务未提交文件；不改二维码120秒、天气及设备接口。

## Review Focus

- 修改其他员工不使本人的待发布结果无效；本人读音/音色/姓名变化或离职必须阻止发布。
- 发布从最新正式清单合并，不丢其他员工映射、音频或署名；旧全员结果不会被误当单员工发布。
- 同组部分人员已更新时，保留其他人员原组的实际参数与署名。
- 页面明确任务和发布范围，单员工按钮不触发全员合成；轮询不重建正在编辑的员工输入。
- 旧草稿、旧全员任务和旧音频仍可读取。

### Task 1: 单员工任务与清单合并

Files: hrms/utils/attendance_voice_settings.py、hrms/api/attendance_voice_settings.py、hrms/utils/attendance_sign_audio.py、hrms/tests/test_attendance_voice_settings.py。

- [x] RED：本人两段合成/范围状态、其他人修改不阻止发布、本人变更/离职拒绝、非法员工、合并保留其他人和署名、空清单和旧16k兼容。
- [x] 实现可选employee_id、局部fingerprint和逐员工原子合并发布；全员接口参数向后兼容。
- [x] 设置38、引擎6、CSV准备9及设备19相关回归GREEN（共72项），Ruff通过并提交。

### Task 2: 操作入口与部署

Files: hrms/hr/page/attendance_voice_settings/attendance_voice_settings.js、docs/attendance-voice-settings.md及本计划。

- [x] 员工行新增“仅生成本人”及待生成完成后的“发布本人”；顶部显示明确的员工姓名、两段进度和发布范围；保留全员入口。
- [x] 隔离真实浏览器/GPU验证只合成两段并手动发布，映射人数保持8、其余7人清单和音频SHA完全不变，375px操作可用。
- [ ] gpt-6-luna / medium独立审查，提交、快进部署；正式页面/权限及设备回归、正式草稿与清单保留。
- [ ] 停止测试web和临时worker、恢复正式租约服务及隔离配置，交付页面入口和使用步骤。
