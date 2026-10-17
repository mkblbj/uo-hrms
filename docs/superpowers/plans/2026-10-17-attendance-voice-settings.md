# 中文考勤语音设置实施计划

> 执行方式：superpowers:executing-plans，当前会话直接实施；最终独立审查使用 gpt-6-luna / medium。

**Goal:** 管理员通过中文网页改假名、音色、试听、生成与发布。
**Architecture:** Desk Page + 受角色保护的API + 私有草稿和待发布资源；租用文件驱动宿主机按需GPU服务。
**Tech Stack:** 当前Frappe/Python、普通JavaScript/CSS、VOICEVOX/Nemo、Docker Compose、systemd用户服务。
**Spec:** `docs/superpowers/specs/2026-10-17-attendance-voice-settings-design.md`

## Global Constraints

保留所有无关未提交工作；设备接口v1和PWA不改；试听和生成不自动发布；已发布资源始终可用；全部在职员工；只读姓氏＋さん＋固定日语问候；管理员权限；GPU优先，空闲60秒停机。

## Review Focus

未授权调用、草稿竞争更新、过时生成发布、失败时旧音频、页面转义与按钮状态。

### Task 1: 草稿与发布服务

Files: `hrms/utils/attendance_voice_settings.py`、`hrms/api/attendance_voice_settings.py`、`hrms/tests/test_attendance_voice_settings.py`；小范围复用音频校验/发布函数。
- [x] 编写并观察失败测试：角色限制、草稿持久化与冲突、姓名保持、预览不发布、生成后待发布、发布版本/员工快照校验、失败保留当前manifest。
- [x] 实现私有文件读写与锁、设置返回、预览下载、后台任务和受保护发布；测试转绿。

### Task 2: 引擎与按需GPU生命周期

Files: `hrms/utils/attendance_voice_engine.py`、`deploy/attendance-voice.compose.yaml`、`deploy/attendance_voice_engine_worker.py`、对应测试。
- [x] 先测引擎租用、只接受固定引擎、超时/错误、无租用关闭、音频格式；再实现租用文件与受限宿主worker。
- [x] 普通VOICEVOX固定镜像与真实角色列表、假名试听、全员资源生成实测；Nemo保持可选。

### Task 3: 中文Desk页面

Files: `hrms/hr/page/attendance_voice_settings/{__init__.py,attendance_voice_settings.json,attendance_voice_settings.js}`。
- [x] 中文全员读音表、搜索、引擎/角色/风格/语速、试听播放器、草稿保存、生成进度和发布按钮。
- [x] 页面转义、键盘焦点、失败保留数据；实测桌面/375px和预览、生成、发布流程（隔离站点）。

### Task 4: 验证与上线

- [x] 相关服务器测试、原签到回归、GPU真实试听、后台任务及人工发布隔离测试。
- [ ] gpt-6-luna / medium审查；修复重要问题；仅合入本功能文件。
- [ ] 部署管理页与宿主引擎worker、验证正式权限和预览；保留正式现有声音，用户决定何时发布新声音。
- [ ] 交付中文页面地址与操作说明。
