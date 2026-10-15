# 服务器验证记录

日期：2026-10-15（Asia/Tokyo）。开发基线：`c71a4c45f`，分支：`feat/attendance-sign-server`。

## 功能与回归

在新建隔离站点 `attendance-sign-test.localhost` 验证，未在生产站点创建虚构打卡。

| 测试模块 | 结果 |
| --- | --- |
| `hrms.tests.test_attendance_sign` | 14 项通过，包含真实数据库与独立 HTTP 请求 |
| `hrms.tests.test_attendance_sign_prepare` | 5 项通过，使用本地 HTTP 测试服务器验证 Nemo 请求与 WAV 输出 |
| `hrms.tests.test_checkin_service` | 6 项通过 |
| `hrms.tests.test_qr_attendance` | 7 项通过 |
| `hrms.tests.test_passkey_api` | 18 项通过 |
| `hrms.tests.test_qr_display_key` | 4 项通过 |

合计 54 项通过。另有 Ruff 检查、格式化和 Compose 配置检查通过。此处为相关服务器模块验证，不代表运行过整个 ERP/工资测试集。

接口验证内容：地点密钥缺失/错误/禁用拒绝；网页免密设置不绕过设备鉴权；只返回目标地点最近新建的 QR/Passkey IN/OUT，过滤修正、过期和未来记录；同时间稳定排序与 20 条上限；缺音频与改名的清单不匹配时返回 null；音频哈希、采样率、声道、时长校验；无任意路径下载；导入失败保留旧清单。独立 HTTP 请求验证已提交记录可读、回滚记录不可读，并下载到实际 WAV 字节。

## Nemo GPU 实测

- GPU：NVIDIA GeForce RTX 3080，10 GiB 显存。
- 引擎：官方 Nemo NVIDIA 镜像，摘要固定在 Compose 中；`supported_devices` 返回 `cuda=true`，实际启动带 `--use_gpu`。
- 配额：1 CPU、2 GiB 容器内存，NVIDIA GPU；生成顺序执行。
- 声音：女声1 / ノーマル，style ID `10005`。这是虚构样音的暂定声音，真实员工应试听确认。
- 合成虚构员工“山田太郎”，假名呼叫名“ヤマダ”，两个完整问候合计耗时 **1.456 秒**。
- 签到：**2.507 秒**、**80258 字节**；签退：**2.165 秒**、**69334 字节**。
- 两段均已通过 mono / PCM16 / 16000 Hz / 最长 5 秒校验。
- 容器内存峰值 **411779072 字节，约 393 MiB**；采样时引擎进程使用显存 **494 MiB**。这是本次样音实测，不是所有批量/声音配置的固定上限。
- 合成后引擎已停止，释放运行内存和显存。GPU 镜像保留在磁盘以便后续按需启动。真实合成资源包也已在隔离测试站点成功导入，共 2 个片段。

音声来源：VOICEVOX Nemo（女声1）。样音均为虚构姓名，不含真实员工信息。

## 尚未完成的范围

- 生产站点未部署本分支；当前测试结果不等于正式接口已上线。
- 尚无真实试点人员确认过的假名 CSV，未批量生成真实员工音频。
- 本机固件、烧录、屏幕显示及扬声器发音由本机完成，尚未做真板联调。

运行与部署见 [服务器操作说明](attendance-sign-server.md)。

## 独立代码审查

已由 `gpt-6-luna`、`medium` 审查两次功能提交及操作说明：Critical、Important、Minor 均无，未搁置审查项，结论可合入。
