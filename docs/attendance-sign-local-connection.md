# 直接交给本机 Codex：实现会回应的签到牌

服务端已于 2026-10-15 合并并部署到正式 HRMS。请在连接 ESP32-S3-RLCD-4.2 的本机直接实施固件；服务器端已完成，不需要在本机部署 HRMS 或 TTS。

## 已上线的服务

- HTTPS 基础地址：`https://erphr.toiroworld.com`
- 打卡地点：`uo-2f-door`（UO 本社 2階 オフィス）。
- 全部 28 名在职员工已覆盖，签到/签退共 56 个语音映射、52 个去重 WAV 文件。
- 服务器使用 VOICEVOX Nemo、RTX 3080 提前生成语音，生成完成已经停止引擎。
- 本次使用女声1 / ノーマル，style ID 10005。姓名使用当前姓名的默认日语读法；个别人名可在服务器修正 `spoken_name` 后重新生成。
- PWA 继续原有打卡操作；板子只接收成功记录，显示姓名并播放对应问候。

## 本机配置

同包的 `device-config.private.json` 已包含实际地址、地点、密钥、请求 User-Agent 和可直接试听的正式音频地址。请读取此文件，把配置保存到本机被 Git 忽略的 `main/sign_config.local.h` 或等效私有配置中；不要把实际密钥写入代码提交或普通日志。

字段与固件配置的对应关系：

| JSON 字段 | 用途 |
| --- | --- |
| `base_url` | HTTPS 基础地址 |
| `location` | 地点 ID |
| `header_name` | 密钥请求头名，值为 `X-Attendance-Sign-Key` |
| `display_key` | 上述请求头的实际密钥 |
| `user_agent` | 请求 User-Agent，已验证为 `UO-Attendance-Sign/1.0 (ESP32-S3)` |
| `test_audio_urls.IN` / `.OUT` | 已验证可下载的正式音频相对地址，用于验证 TLS、下载及播放 |

Wi-Fi 名称和密码只在本机配置。实际密钥只存在私有配置文件中，本文可单独转发。

## 接口 1：读取新近打卡

```text
GET https://erphr.toiroworld.com/api/method/hrms.api.attendance_sign.get_events?location=uo-2f-door
X-Attendance-Sign-Key: 从私有配置读取
User-Agent: UO-Attendance-Sign/1.0 (ESP32-S3)
```

响应是 Frappe `message` 包装的 JSON。下例为虚构数据，正式字段名一致：

```json
{
  "message": {
    "version": 1,
    "server_time": 1792022521,
    "locale": "ja-JP",
    "events": [
      {
        "id": "example-checkin-id",
        "employee_id": "example-employee-id",
        "employee_name": "山田太郎",
        "log_type": "IN",
        "time_label": "09:02",
        "created_at": 1792022520,
        "action_label": "出勤完了",
        "greeting": "おはようございます。",
        "audio_url": "/api/method/hrms.api.attendance_sign.get_audio?location=uo-2f-door&asset_id=64位SHA256"
      }
    ]
  }
}
```

- 在线每秒请求一次；每次仅返回该地点最近 30 秒新建的 QR/Passkey 成功 IN/OUT，最多最新 20 条，按先后顺序返回。
- 没有新打卡时 `events` 为空是正常情况。当前没有轮询游标参数。
- 首次成功连接或断线恢复时，用首批 ID 建立基线，不播放这些历史条目；从下一批开始按 `id` 去重并排队处理新条目。
- 最近 ID 保留 64 个，待播队列最多 20 条；队列满时丢弃最旧的待播项，当前播放不打断。不补播离线积压。
- 请求超时 3 秒，失败后 5 秒重试；失败清空待播项，当前反馈结束后显示离线；恢复后重新建立基线。
- `server_time`、`created_at` 为 Unix 秒；屏幕直接用 `time_label`，不要把服务器的站点时间重复换时区。
- 缺失、错误或跨地点密钥，以及禁用地点，返回 403；响应不缓存。

## 接口 2：下载并播放对应语音

把 `audio_url` 作为相对地址拼接到上述 HTTPS 基础地址，继续带同样的密钥请求头和 User-Agent。响应为实际 WAV 文件字节，`Content-Type: audio/wav`，不套 JSON。

格式：WAV / PCM signed 16-bit little-endian / 16000 Hz / 单声道 / 最长 5 秒。下载到 PSRAM 后通过板载 ES8311 扬声器路径播放；本机不运行 Nemo、不使用 SD 卡、不调用云端 TTS。

`audio_url=null` 或下载失败时照常显示姓名、动作和时间，播放固件内置短提示音并继续下一人。正式音频已经生成，空值主要用于新入职、改名或音频尚未更新的情况。

公网已用 `UO-Attendance-Sign/1.0 (ESP32-S3)` 和默认 `ESP32 HTTP Client/1.0` 验证通过；Python 的默认 urllib User-Agent 曾被 Cloudflare 返回 403，因此本机调试脚本也应显式设置约定的 User-Agent。保持 HTTPS 服务器证书校验。

## 固件实施范围

1. 检查本机现有工程、ESP-IDF 与实际串口；若无现成工程，新建独立 `attendance-sign` 工程。使用 ESP-IDF 5.5.2，复用微雪显示/I2C/音频例程。不要照搬服务器文件路径或旧串口名。
2. 用包内虚构 JSON 和两段虚构样音，先验证屏幕、中文/日文字形与扬声器。
3. 用私有配置中的 `test_audio_urls` 验证正式 HTTPS 音频下载与播放。这是接入测试，不代表有人打卡，也不创建考勤记录。
4. 连接正式 `get_events`：屏幕显示员工姓名、`action_label`、`time_label`、`greeting`，同时播放对应音频；每条反馈显示 5 秒，然后下一条或回待机。网络轮询与显示播放分开执行。
5. 待机显示时间、连接状态；不增加刷卡、触摸、麦克风录音、二维码迁移或 PWA 修改。
6. 完成后由实际员工按原 PWA 流程签到/签退，核对姓名、动作和声音；验证多人排队、重复轮询、重启、断网与恢复。不要用脚本制造正式站点虚构打卡。
7. 报告固件版本、实际串口、编译/烧录结果、真屏截图或视频及声音结果。服务器验证通过不代替本机真板验证。

代码审查统一使用 `gpt-6-luna`，推理强度 `medium`。如委派审查，显式设置这两个参数。

## 正式部署验证

合并后的 54 项服务器测试全部通过；公网已验证：无密钥/错误密钥均 403，正确密钥的事件接口 200，IN/OUT WAV 下载均 200 且格式与哈希正确，原 PWA 与 ping 返回 200。没有在正式站点创建虚构打卡记录。

附带的 `demo-in.wav`、`demo-out.wav` 是虚构“山田太郎”的开发样音，音声来源：VOICEVOX Nemo（女声1）。正式设备或旁边标注“音声：VOICEVOX Nemo”。
