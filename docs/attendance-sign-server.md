# 会回应的签到牌：服务器端操作与交接

状态：2026-10-15 已合并并部署到正式 HRMS；公网入口、地点鉴权与 WAV 下载验证通过。全部 28 名在职员工已配置 56 段语音映射。本机固件及真屏播放仍由本机完成。

当前试听及新生成资源统一24kHz、PCM16、单声道、最长5秒，完整WAV上限256KiB。升级前的正式16k资源保留到用户单独发布新资源；本机调整见[24k固件交接](attendance-sign-24khz-firmware-handoff.md)。

## 运行方式

服务器提前生成日语问候，支持 VOICEVOX Nemo 和普通 VOICEVOX 角色音色。优先 NVIDIA GPU，不可用时手动选 CPU。合成完成关闭引擎，日常打卡只读取已保存音频，不运行 TTS。

日常维护使用[中文考勤语音设置页面](attendance-voice-settings.md)：管理员可改每人姓氏假名、选音色、试听，生成后单独发布。以下命令行流程继续可用。设备只有两个只读接口，PWA、打卡校验、工时计算均无修改。

## 1. 按需启动 Nemo

以下 Compose 命令在服务器 HRMS 应用仓库根目录执行。`NEMO_NETWORK` 必须是 Frappe 容器所在的现有 Docker 网络；本服务器为 `docker_default`。引擎使用网络别名 `attendance-sign-nemo`，供同网络的 Frappe 容器访问；主机端口仅绑定 `127.0.0.1:50121`。

```bash
NEMO_NETWORK=docker_default docker compose -f deploy/attendance-sign-nemo.compose.yaml --profile gpu up -d nemo-gpu
```

GPU 容器限制 1 CPU、2 GiB 主机内存，使用一块 NVIDIA GPU。Compose 固定镜像摘要，需驱动与 NVIDIA Container Toolkit。无 GPU 时先停止原引擎，再选择 CPU：

```bash
docker compose -f deploy/attendance-sign-nemo.compose.yaml down
NEMO_NETWORK=docker_default docker compose -f deploy/attendance-sign-nemo.compose.yaml --profile cpu up -d nemo-cpu
```

CPU 容器限制 1 CPU、1 GiB 内存。不要同时启动两种引擎，它们共享端口和网络别名。GPU 镜像本机大小约 5.54 GB（十进制），CPU 镜像约 1.20 GB；镜像保留在磁盘，不等于运行内存。

查看声音（在服务器主机执行）：

```bash
curl --fail --silent http://127.0.0.1:50121/speakers
curl --fail --silent http://127.0.0.1:50121/supported_devices
```

本次虚构样音使用 `女声1 / ノーマル`，style ID `10005`。ID 应以运行中引擎返回结果为准。

## 2. 准备员工 CSV

由 HR 管理员从当前员工信息中整理目标人员，在服务器私有目录保存 UTF-8 CSV，不提交到 Git。`employee_id` 使用真实 Employee 文档 ID；`employee_name` 与 HRMS 显示名一致；`spoken_name` 是经员工确认的日语假名呼叫名，日常维护优先使用确认过的假名。本次按用户要求全部启用，首批直接使用当前姓名的 Nemo 默认日语读法，之后可逐人修正。

```csv
employee_id,employee_name,spoken_name
HR-EMP-example,山田太郎,ヤマダ
```

上述为虚构示例。工具自动添加一次“さん”；姓名字段末尾已有“さん”也不会重复。固定文本：签到“ヤマダさん、おはようございます。”，签退“ヤマダさん、お疲れさまでした。”。

## 3. 生成并导入

以下 Python/bench 命令在运行 HRMS 的容器内、该站点的 bench 根目录执行，使用该 bench 的 Python 环境。CSV 路径和输出路径也必须是容器内可见的绝对路径。`engine-url` 使用容器网络别名；容器中的 `localhost` 不指向宿主机。

```bash
env/bin/python -m hrms.utils.attendance_sign_prepare \
  --input-csv /absolute/private/employees.csv \
  --output /absolute/private/attendance-sign-bundle \
  --engine-url http://attendance-sign-nemo:50121 \
  --speaker-id 10005
```

工具先校验所有 CSV 行，再顺序合成；输出版本 1 的 `manifest.json` 和按 SHA-256 命名的 WAV。每段必须是 24 kHz、单声道、16-bit PCM 且不超过 5 秒。姓名较长导致超时时，调整 `--speed 1.1` 等参数后重做并试听；不裁掉未播完的名字。全部片段通过后才替换清单，失败保留之前的有效清单。

以 System Manager / bench 管理员导入目标站点：

```bash
bench --site YOUR_SITE execute hrms.utils.attendance_sign_audio.install_bundle \
  --kwargs '{"source_dir":"/absolute/private/attendance-sign-bundle"}'
```

导入结果包含 `clips` 和 `assets` 数量，文件位于 `sites/YOUR_SITE/private/attendance-sign/`，不放在公开 `files` 目录。导入是清单整体替换；更新部分人员时 CSV 仍应包含希望继续提供语音的全部试点人员。显示名变更后，旧清单不再匹配新姓名，重新生成后导入。

准备完成在服务器主机停止引擎：

```bash
docker compose -f deploy/attendance-sign-nemo.compose.yaml down
```

## 4. 板端接口

动态二维码新增 `GET /api/method/hrms.api.attendance_sign.get_qr?location=地点ID`，同样必须带设备密钥请求头。uo-2f-door配置为120秒换码，网页、公开API和板端共用签名逻辑；服务器仍接受当前和上一时槽。具体字段、硬过期及本机显示方案见[二维码常驻接入说明](attendance-sign-qr-display-handoff.md)。

板子通过可从其 Wi-Fi 网络访问的 HRMS HTTPS 入口连接，不使用服务器 localhost 或 Docker 容器名。

- `GET /api/method/hrms.api.attendance_sign.get_events?location=地点ID`
- `GET /api/method/hrms.api.attendance_sign.get_audio?location=地点ID&asset_id=SHA256`
- 两者请求头：`X-Attendance-Sign-Key: 该地点的display_key`。密钥通过本机未提交配置传递，不写入 URL 或日志。
- 地点必须存在且启用；即使网页设置不要求密钥，这两个设备接口仍检查密钥。
- 第一个接口返回 Frappe `message` 包装的 v1 数据，仅含该地点最近 30 秒新建的 QR/Passkey IN/OUT，最多最新 20 条，按先后顺序返回。
- 第二个接口返回实际 `audio/wav` 文件内容；音频地址为同源相对路径，下载时继续携带请求头。
- `audio_url=null` 表示该员工没有匹配音频。板子照常显示文字，使用内置短提示音。
- 板子首连与重连只建立 ID 基线，之后每秒轮询、去重，并按本机计划排队回应。

虚构数据见 [fixtures](attendance-sign/fixtures/)。设备不需要安装 Nemo，也不把录音或员工身份信息发给 Nemo；板子只下载服务器提供的已生成文件。

## 5. 验证与部署

新增测试：

```bash
bench --site attendance-sign-test.localhost run-tests --app hrms --skip-before-tests --module hrms.tests.test_attendance_sign
env/bin/python -m unittest hrms.tests.test_attendance_sign_prepare
```

上述站点为隔离测试站点，不能换成生产站点直接运行。相邻回归模块：`hrms.tests.test_checkin_service`、`hrms.tests.test_qr_attendance`、`hrms.tests.test_passkey_api`、`hrms.tests.test_qr_display_key`。

独立 HTTP 验证包含：记录提交后可读、回滚记录不可读、实际 WAV 下载。Nemo 真合成、资源实测与最终测试数量见 [验证记录](attendance-sign-validation.md)。

上线需要把此开发分支合入实际 HRMS 应用，并按项目部署流程重载 Python 服务；本改动没有 DocType/schema 迁移，也不需要构建 PWA。确认目标地点和展示密钥，导入真实试点音频后，再交给本机进行实际签到、签退、连续多人、重启和断网验证。未完成上线前，不把正式站点地址交给板子作为已可用接口。

停用时停止引擎并让板子离线即可，既有打卡继续工作。需要移除接口时回退本分支新增文件并重载 Python 服务；私有音频目录保留供恢复。

## 音声来源

音声合成：VOICEVOX Nemo。本次样音为女声1。正式使用在设备或旁边标注“音声：VOICEVOX Nemo”，按所选声音的适用条款保留署名；生成清单也记录来源。

参考：[Nemo Engine](https://github.com/VOICEVOX/voicevox_nemo_engine)、[Nemo 使用条款](https://voicevox.hiroshiba.jp/nemo/term/)。

## 正式接入

已部署地址 `https://erphr.toiroworld.com`，地点 `uo-2f-door`。直接发给本机 Codex 的说明见 [本机接入说明](attendance-sign-local-connection.md)。密钥通过单独的私有配置交付，不写入文档或 Git。
