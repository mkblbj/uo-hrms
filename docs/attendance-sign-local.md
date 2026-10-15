# 会回应的签到牌：本机固件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 如委派代码审查，按用户要求使用 `model="gpt-6-luna"`、`reasoning_effort="medium"`。

**Goal:** 在用户本机为 ESP32-S3-RLCD-4.2 制作并验证会显示姓名、播报签到及签退问候的固件。

**Architecture:** 本机独立 ESP-IDF 工程，复用微雪的屏幕和音频驱动；通过 HTTPS 每秒获取服务器接口 v1，按 ID 去重、排队显示和播放。姓名音频由服务器使用 VOICEVOX Nemo 提前生成，本机负责试听与播放验证。

**Tech Stack:** ESP-IDF 5.5.2、C++17、FreeRTOS、esp_http_client、cJSON、微雪 LVGL 8 屏幕/音频例程。

**Spec:** `2026-10-15-attendance-sign-design.md`，由服务器交接；接口与资源包 v1 为唯一依据。

## Global Constraints

- 只在板子连接的本机执行此计划。服务器绝对路径与 USB 串口名不可直接用于本机。
- 已有固件目录尚未确认；先检查本机项目，若没有则新建独立 `attendance-sign/`。下列路径全部相对这个固件根目录。
- 板子仅消费成功记录，不创建考勤记录；PWA 沿用当前流程。
- 显示 5 秒；首连/重连只建立基线，按 ID 去重；最近 ID 64 个、待播队列 20 条；超量丢弃最旧待播任务。
- WAV、PCM 16-bit、16 kHz、单声道、最长 5 秒；不依赖 SD 卡和在线 TTS。
- 播报语言已确认为日语 `ja-JP`；用户已选择服务器端 VOI EVOX Nemo 预生成，本机不部署 TTS。具体音色通过样音确认。Mac 系统声音不作为公司设备的正式资源来源。
- 只使用可从本机及板子访问的 HRMS HTTPS 地址；校验服务器证书；地点密钥置于本机未提交配置。

## Review Focus

1. 网络重复返回同一记录，只回应一次。由任务 2 的状态测试覆盖。
2. 板子重启或网络恢复，不播报之前的打卡。由任务 2 的基线测试覆盖。
3. 连续 3 人打卡，姓名与声音配对，显示顺序一致，播放不阻塞网络。由任务 2/3 覆盖。
4. 长姓名或中日韩字形可读，坏音频仍有文字与短提示音。由任务 1/3 实机覆盖。
5. 服务器不可达或返回权限错误，板子显示离线且 PWA 正常工作。由任务 3 联调覆盖。

---

## 文件分工与接口

| 文件 | 职责 |
| --- | --- |
| `CMakeLists.txt`、`sdkconfig.defaults`、`main/CMakeLists.txt` | ESP32-S3、PSRAM、证书包及官方例程匹配配置 |
| `components/port_bsp/` 与对应例程必要依赖 | 固定版本的官方显示、I2C、音频驱动，保留许可证 |
| `main/app_main.cpp`、`main/sign_board.{h,cpp}` | 启动、Wi-Fi、时钟、屏幕、扬声器适配 |
| `main/sign_client.{h,cpp}` | HTTPS 请求、JSON 解析、同源音频下载 |
| `main/sign_presenter.{h,cpp}` | 基线、去重、队列和 5 秒显示播放状态 |
| `tests/CMakeLists.txt`、`tests/test_sign_presenter.cpp` | 不依赖硬件的核心状态测试 |
| `main/sign_config.example.h`、`.gitignore`、`README.md` | 配置样例、私有配置排除、本机操作和实测记录 |

`SignEvent` 在任务 1 中定义于 `main/sign_presenter.h`：`id, employee_id, employee_name, log_type, time_label, action_label, greeting, audio_url` 为 `std::string`，`created_at` 为 double；空音频统一为空字符串。`EventBatch` 同时在该头文件定义，包含 `double server_time` 与 `std::vector<SignEvent> events`。任务 2 再向该头文件加入状态类。

### 任务 1：跑通屏幕和扬声器，接收服务器姓名音频

**Files:** 项目配置、`components/port_bsp/`、`main/sign_board.{h,cpp}`、`main/sign_presenter.h`（数据类型）、`main/app_main.cpp`及 README。

**Interfaces:**
- 消费：官方固定提交 `eb1f63427d735a22b9c30e22fa63ebddae1834d3` 的 `02_Example/ESP-IDF/07_Audio_Test` 与 `08_LVGL_V8_Test`，以及 spec 的资源包格式。
- 产出：`esp_err_t sign_board_init()`、`void sign_board_show(const SignEvent&)`、`void sign_board_idle(bool online)`、`esp_err_t sign_board_play_wav(const uint8_t* data, size_t size, uint32_t timeout_ms)`、`void sign_board_beep()`。

- [ ] **步骤 1：在本机检查项目、工具链和串口。** 记录实际固件目录、ESP-IDF 版本、唯一确认的目标串口。之前检测的串口只作线索，不自动沿用。确认有扬声器，并记录原固件的恢复方式。
- [ ] **步骤 2：编译最小官方显示/播放例程并实机运行。** 使用 ESP-IDF 5.5.2；不运行完整工厂初始化，不依赖 SD。分别显示虚构姓名、播放内置 WAV；尚未烧录前的编译通过不算本步骤完成。
- [ ] **步骤 3：实现数据类型、适配函数和字体。** 先定义供屏幕和后续任务共用的 `SignEvent` / `EventBatch`。从驱动引脚配置出发保留官方初始化顺序；只使用显示和播放路径。核对试点员工字符覆盖与长姓名排版；不启用麦克风录音或语音识别。
- [ ] **步骤 4：接收服务器通过 Nemo 生成的试点音频，逐条试听。** 核对假名呼叫名、敬称、重音、采样率及 5 秒限制，错误读音交回服务器重新生成。音频生成工具和对应测试属于服务器端，本机不重复实现。
- [ ] **步骤 5：提交固件骨架。** 提交说明 `feat: initialize attendance sign display and audio`，不包含真实姓名包、Wi-Fi 或密钥。

### 任务 2：用模拟接口完成去重、排队和显示状态

**Files:** `main/sign_presenter.{h,cpp}`、`tests/CMakeLists.txt`、`tests/test_sign_presenter.cpp`。

**Interfaces:**
- 消费：`EventBatch`、服务器的虚构 JSON 样例、任务 1 的显示与播放适配。
- 产出：`void SignPresenter::accept(const EventBatch&)`、`void SignPresenter::disconnect()`、`std::optional<SignEvent> SignPresenter::next(uint64_t now_ms)`；时间来自单调时钟，同一任务最多占用 5000 ms。

- [ ] **步骤 1：写核心状态失败测试。** `boot_seeds_without_replay`：初次批次不输出；`same_id_only_once`：重复 ID 只输出一次；`burst_keeps_name_and_order`：3 个新 ID 对应三次输出；`reconnect_drops_history`：disconnect 后首批只建基线；`display_lasts_five_seconds`：4999 ms 不换下一人、5000 ms 可换；`overflow_keeps_current_and_latest_twenty`：当前播放不受影响，待播保留最新 20 条。
- [ ] **步骤 2：运行 `cmake -S tests -B build-host`、`cmake --build build-host`、`ctest --test-dir build-host --output-on-failure`，确认新增状态测试失败。**
- [ ] **步骤 3：实现状态核心。** 首连基线、64 个 ID 的有限去重、20 条待播、5 秒显示时间；不在状态核心内调用 Wi-Fi、LVGL 或音频，便于以虚构数据独立验证。
- [ ] **步骤 4：同一组命令通过后，在板上注入 IN、OUT、3 人连续事件。** 检查姓名、声音和顺序；记录截图或短视频供两端对照。
- [ ] **步骤 5：提交本任务。** 提交说明 `feat: queue attendance sign greetings`。

### 任务 3：接 HTTPS 接口，烧录并完成真实联调

**Files:** `main/sign_client.{h,cpp}`、`main/app_main.cpp`、配置样例、README；必要时调整任务 1 的驱动适配。

**Interfaces:**
- 消费：服务器 `get_events` 与 `get_audio`、地点和密钥、本机 Wi-Fi、已准备音频。
- 产出：`sign_client_fetch() -> std::optional<EventBatch>`、`sign_client_fetch_audio(const std::string& relative_url) -> std::vector<uint8_t>`，以及实际烧录固件和本机验证记录。

- [ ] **步骤 1：实现 HTTPS 拉取和配置。** 提供 `main/sign_config.example.h`，实际值放入 Git 忽略的 `main/sign_config.local.h`，包含 `SIGN_HRMS_BASE_URL`、`SIGN_LOCATION`、`SIGN_KEY`、`SIGN_WIFI_SSID`、`SIGN_WIFI_PASSWORD`、`SIGN_VOLUME`。每秒读取一次；请求超时 3 秒，失败后 5 秒重试；恢复后的第一批只建立基线。通过 `esp_crt_bundle_attach` 校验证书，先完成正常校时。只解析 v1 `message`，拒绝异常响应，音频下载沿用同一 HRMS origin 与地点密钥。
- [ ] **步骤 2：接入独立的网络与显示播放任务。** 状态对象的共享访问用一个 FreeRTOS mutex 保护；调用慢速下载及播放时不持有该锁。事件拉取和音频下载各用自己的 HTTP client，播放不阻塞事件拉取。显示当前姓名后下载音频，失败使用短提示音；向 `sign_board_play_wav` 传入当前 5 秒时段的剩余时间，超时停止该条音频并处理下一条。
- [ ] **步骤 3：运行主机状态测试并执行 `idf.py set-target esp32s3`、`idf.py build`。** 预期主机测试通过，生成目标固件且没有新增编译错误。
- [ ] **步骤 4：用本机实际检测的串口执行烧录并读取日志。** 命令形式为 `idf.py -p 实际串口 flash monitor`；记录固件版本和设备启动结果，不使用服务器路径或串口。
- [ ] **步骤 5：用真实 PWA 完成联调清单。** 一次签到、一次签退；连续 3 人间隔 2 秒；重复轮询不重播；失败打卡不回应；缺音频仍显示和提示；断网与重启不补播；同名/长姓名显示及声音一致；无排队正常网络下开始回应目标不超过 2 秒。板子离线期间 PWA 继续正常完成打卡。
- [ ] **步骤 6：记录本机验收与回退方式并审阅差异。** 如委派代码审阅，固定用 `gpt-6-luna` / `medium`。交付成功项、尚未通过项、截图或短视频和固件版本。
- [ ] **步骤 7：提交本任务。** 提交说明 `feat: connect attendance sign to HRMS`。

## 可直接交给本机 Codex 的任务说明

> 请按收到的设计与本机计划实施“会回应的签到牌”。HRMS 在远程服务器，本会话只负责连接在本机的 ESP32-S3-RLCD-4.2。先确认本机固件目录、ESP-IDF 与串口；用服务器提供的虚构接口样例开发显示、姓名语音、去重和队列，再连接实际 HTTPS 接口。PWA 沿用当前流程，不负责修改服务器代码。日语姓名语音由服务器使用 VOICEVOX Nemo 预生成，本机试听并验证播放，板子通过同源受保护接口下载。不得把服务器测试通过当硬件验证通过。播报语言为日语，姓名假名需本人确认；已选择服务器端 VOICEVOX Nemo，具体音色由样音确认，不使用 Mac 系统声音生成公司设备正式资源。完成后报告固件版本、实际显示与声音结果、联调记录。若委派代码审查，使用 gpt-6-luna，推理强度 medium。
