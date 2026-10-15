# 会回应的签到牌：第一版设计与两端接口

日期：2026-10-15。状态：方案范围已获认可，以下实现取舍供规划审阅，服务器端已合并部署生产，本机固件待联调。

## 目标与范围

员工继续使用当前 PWA 完成签到、签退。记录保存成功后，ESP32-S3-RLCD-4.2 显示员工姓名、打卡动作与时间，并播报带名字的欢迎语或结束语。

- 签到示例：屏幕显示“山田太郎／出勤完了／09:02”，语音“山田さん、おはようございます。”
- 签退示例：屏幕显示“山田太郎／退勤完了／18:05”，语音“山田さん、お疲れさまでした。”
- 每条反馈显示 5 秒；多人连续打卡按接收顺序播放。
- 板子仅消费成功记录，不负责识别员工、创建考勤记录或判断打卡是否有效。
- 第一版沿用 PWA、二维码和 Passkey 的现有流程；待机显示时间与连接状态。把二维码迁移到板子不在本次范围内。
- 第一版使用 USB 持续供电、一个打卡地点、一块板子。语音预先生成，打卡过程中不调用在线 TTS。

## 环境与分工

| 工作 | 服务器端（当前会话环境） | 用户本机（板子所在电脑） |
| --- | --- | --- |
| 代码 | HRMS 的只读设备接口、接口测试、部署说明 | 独立 ESP-IDF 固件工程、板端测试 |
| 音频 | 按需启动 VOICEVOX Nemo 预生成、导入并提供下载 | 试听姓名与发音、验证扬声器 |
| 验证 | 接口、权限、成功记录、音频下载、现有打卡回归 | 显示、扬声器、Wi-Fi、编译、烧录、真实打卡回应 |
| 联调 | 交付可访问的 HTTPS 地址与地点配置 | 配置地址、密钥，实测屏幕和声音 |

当前服务器看不到本机 USB。服务器通过测试不能替代本机实测。开发和联调均不依赖 USB 转发或服务器主动连接板子；板子通过 Wi-Fi 主动访问 HRMS 的 HTTPS 地址。

## 已核对的现状

- `apps/hrms/hrms/api/checkin_service.py` 的 `create_checkin()` 是 QR、Passkey 的共用落库入口。
- `publish_checkin_notification()` 已通过 `after_commit=True` 向网页发送姓名、方向、地点和时间。
- 网页订阅使用 Socket.IO。第一版板端选择 HTTPS 短轮询，直接读取同一批已提交记录，不移植网页协议，现有通知保留。
- `get_recent_checkins(compact=1)` 已存在，但未包含姓名，也不是本次专用的地点密钥接口。新增独立接口，保留它的现有返回格式。
- 地点已有 `display_key`。设备接口始终要求实际密钥匹配，不受 `require_display_key=0` 时网页可免密的设置影响。
- 当前根目录和 HRMS 应用均有其他工作留下的改动。实施时隔离改动，不覆盖这些文件。
- 检测记录显示板子运行 ESP-IDF 5.5.2 工厂固件，曾出现 SD 初始化超时；屏幕和扬声器还没有实际验证。本版本不依赖 SD 卡。

## 两端共用接口 v1

基础地址记为 `HRMS_BASE_URL`，必须是本机网络及板子可访问的 HRMS HTTPS 入口，不能使用服务器的 `localhost`、容器名或仅服务器可达的内网地址。地点记为 `LOCATION`。

所有设备请求通过请求头 `X-Attendance-Sign-Key` 提交该地点的展示密钥。密钥不放进网址、示例数据、提交记录或普通日志。

### 读取近期成功记录

`GET /api/method/hrms.api.attendance_sign.get_events?location=LOCATION`

Frappe 外层结构仍为 `{"message": {...}}`，内部结构如下，时间与姓名均为虚构示例：

```json
{
  "version": 1,
  "server_time": 1792022401.0,
  "locale": "ja-JP",
  "events": [
    {
      "id": "EMP-CKIN-example",
      "employee_id": "HR-EMP-example",
      "employee_name": "山田太郎",
      "log_type": "IN",
      "time_label": "09:02",
      "created_at": 1792022400.0,
      "action_label": "出勤完了",
      "greeting": "おはようございます。",
      "audio_url": "/api/method/hrms.api.attendance_sign.get_audio?location=LOCATION&asset_id=HEX_SHA256"
    }
  ]
}
```

- 固定读取该地点最近 30 秒新建的、已提交的 `Employee Checkin`，只包含 `checkin_method` 为 `QR` 或 `Passkey`、`log_type` 为 `IN` 或 `OUT` 的记录。
- 按 `creation desc, name desc` 选最近 20 条，再按相反顺序返回。使用新建时间而非可被补填的打卡时间作为新鲜度依据。
- `server_time`、`created_at` 是 Unix 秒。`time_label` 按 HRMS 站点时区格式化，不由板子重新解释服务器的无时区日期字符串。
- 未准备音频、清单中的姓名与当前姓名不符时，`audio_url` 为 `null`，文字照常返回；不能播报旧姓名。
- 成功响应使用 `Cache-Control: no-store`；错误密钥、缺失密钥或禁用地点不返回姓名及音频。
- 首次成功连接及断线后的首次成功连接只建立已有 ID 基线，不播放历史记录；从下一次响应开始处理新 ID。
- 在线时每秒拉取一次，按 `id` 去重。板端保留最近 64 个 ID，待播队列最多 20 条；超量时丢弃最旧的待播条目，当前播放不中断。本版本不承诺为离线、超出窗口或超量记录补播。

### 下载音频

`GET /api/method/hrms.api.attendance_sign.get_audio?location=LOCATION&asset_id=HEX_SHA256`

同样校验地点密钥。只返回当前音频清单引用的文件，文件名为 64 位小写十六进制 SHA-256 加 `.wav`；不接受任意路径。响应为 `audio/wav` 的实际文件内容，不是 JSON 包装或登录网页。

音频采用 WAV、PCM signed 16-bit little-endian、16 kHz、单声道、最长 5 秒。板端使用同一 HTTPS 地址和请求头下载到 PSRAM 播放，不访问任意外部音频域名。下载或播放失败时显示反馈并播放固件内置短提示音，继续处理下一人。

## 音频资源包 v1

服务器从 HR 管理员通过现有员工导出功能提供的 CSV 准备试点人员音频。CSV 列为 `employee_id,employee_name,spoken_name`；`employee_name` 保持 HRMS 的显示姓名，`spoken_name` 为员工确认的日语假名呼叫名（例如“ヤマダ”），合成时加“さん”。按用户要求全部在职员工启用，首批使用现有姓名的 Nemo 默认日语读法；个别人名可在该列修正为确认后的假名后重新生成。屏幕姓名与呼叫名由同一员工 ID 关联。

输出 `manifest.json` 与 `audio/<sha256>.wav`。清单结构：

```json
{
  "version": 1,
  "locale": "ja-JP",
  "clips": {
    "HR-EMP-example": {
      "IN": {"asset_id": "HEX_SHA256", "employee_name": "山田太郎"},
      "OUT": {"asset_id": "ANOTHER_HEX_SHA256", "employee_name": "山田太郎"}
    }
  }
}
```

服务器导入到 `sites/<site>/private/attendance-sign/`，只通过受地点密钥保护的接口提供。员工入职、改名或修正读音时重新准备对应资源，不需要重烧固件。

用户已确认使用 VOICEVOX Nemo，在服务器提前生成日语音频，首版语言为 `ja-JP`。优先采用 NVIDIA GPU 模式，不可用时使用 CPU；只在准备或更新资源时启动引擎，生成完关闭；不占用日常打卡链路，不同时开发其他合成器或语言切换。具体音色通过 Nemo 的声音列表选择，试点样音使用首个可用普通声音并明确标注。未收到固件工程路径，按本机新建独立 `attendance-sign` 工程规划。

此前把 Mac 系统 `say` 列为正式音频来源的建议已撤回：Apple 系统声音的导出内容有个人非商用用途限制，不作为本公司设备的正式语音来源。VOICEVOX Nemo 允许注明来源后商用；若选用，资源包交付说明记录声音来源，并在设备或旁边标注相应音声来源。本次不接入云端 TTS，打卡过程中直接播放预制文件。

## 板端显示与播放

- 状态：连接中、待机、回应、离线。待机时钟由已校时的本机时间更新；未校时显示占位，不显示错误时间。
- 姓名最多两行，长姓名按屏幕宽度缩小字号；包含姓名所需的中日韩字形，不以缺字方块代替。截图与真屏共同检查。
- 同一人的屏幕反馈和声音属于同一条任务；5 秒内播完，进入下一条。网络拉取与显示播放分开执行，不因播放阻塞拉取。
- 请求超时为 3 秒，失败后 5 秒重试；首次失败清空未播放队列，当前任务结束后显示离线。恢复时建立基线，之后恢复每秒轮询。
- 设备本地配置包括 HTTPS 地址、地点、密钥、Wi-Fi、音量；实际配置不提交。第一版使用被 Git 忽略的 `main/sign_config.local.h` 配置头文件，不开发配网 App、远程设备管理、OTA 或麦克风功能。

## 完成标准与交付次序

1. 服务器先交付接口说明及虚构 `IN`、`OUT`、多人、缺少音频的 JSON 样例；本机可据此独立开发。
2. 服务器按需启动 Nemo 生成试点语音并导入；本机跑通官方屏幕和音频驱动，试听实际发音。
3. 服务器在隔离测试站点验证接口和原有打卡流程，交付正式可访问地址、地点及通过本地配置传递的密钥。
4. 本机连入接口：普通网络下无排队时，提交成功至开始回应目标不超过 2 秒；连续 3 人、间隔 2 秒的打卡均依序回应且不重播。
5. 实测失败打卡不回应、重启及断网恢复不补播旧记录、板子离线时 PWA 继续正常打卡；屏幕姓名和语音姓名一致。服务器测试通过与本机验证通过分别记录。

## 参考

- [微雪 ESP-IDF 教程：最低版本、显示和音频例程](https://docs.waveshare.net/ESP32-S3-RLCD-4.2/ESP-IDF/)
- [微雪官方示例仓库](https://github.com/waveshareteam/ESP32-S3-RLCD-4.2)，规划核对的提交为 `eb1f63427d735a22b9c30e22fa63ebddae1834d3`。
- [ESP-IDF 5.5.2 HTTPS 客户端](https://docs.espressif.com/projects/esp-idf/en/v5.5.2/esp32s3/api-reference/protocols/esp_http_client.html)。
- [VOICEVOX Nemo](https://voicevox.hiroshiba.jp/nemo/) 与[使用条款](https://voicevox.hiroshiba.jp/nemo/term/)。
- [Azure 日语声音列表](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts)。
- [Apple macOS Tahoe 许可 2.F](https://www.apple.com/legal/sla/docs/macOSTahoe.pdf)。
