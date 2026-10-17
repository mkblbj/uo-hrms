# 考勤语音设置

管理员页面：[考勤语音设置](https://erphr.toiroworld.com/desk/attendance-voice-settings)。需要登录具有 **HR Manager** 或 **System Manager** 角色的后台账号。

## 使用方法

1. 选择“VOICEVOX · 角色音色”或“Nemo · 通用音色”，点击“加载音色”，再选角色、风格和语速。首次唤醒引擎需要几秒时间。
2. 搜索员工，在“姓氏读音（假名）”中只填姓的日语假名，例如王小明填 `ワン`。不填名字或 `さん`，页面仍显示完整姓名。留空时采用“自动姓氏”列，优先使用员工资料中的姓；自动推断不准确时直接填假名覆盖。
3. 点击员工旁的“试听签到”或“试听签退”。试听使用当前输入，无需先保存；播放器也可以重播。全员共用所选音色、风格和语速，每人的姓氏读音分别保存。
4. 点击“保存草稿”保存进度；以后重新打开页面可以继续编辑。
5. 满意后点击“生成全员语音”，等待全部生成完成。它包含当前所有在职员工的签到、签退语音；此时签到牌仍使用旧声音。
6. 确认后单独点击“发布到签到牌”，新声音才生效。日常更换音色无需修改手机PWA；本次24k格式升级需要先按[固件调整说明](attendance-sign-24khz-firmware-handoff.md)更新本机播放及缓冲配置，再发布。

签到固定为 `ワンさん、おはようございます。`；签退固定为 `ワンさん、お疲れさまでした。`。试听与新生成统一24kHz、PCM16、单声道，完整WAV上限256KiB。每段最多 5 秒；如超长，请提高语速或缩短输入。

音色变更、读音修改或员工资料变化后，应重新生成再发布。生成失败不会替换当前已发布的音频；页面保留输入，可修改后重试。另一个窗口修改了草稿时会提示刷新，避免互相覆盖。

声音来源会显示在音色选择和试听区域，并记录在发布清单。普通角色音色示例为 `VOICEVOX:四国めたん`，Nemo 为 `VOICEVOX Nemo`。更换角色后，设备旁的声音署名也应对应更换。

## 服务器部署

页面是 Frappe Desk Page，无需构建 PWA，也没有数据库字段迁移。在应用代码部署后，从正式 bench 容器执行：

```bash
bench --site hrms.localhost reload-doc hr page attendance_voice_settings
bench --site hrms.localhost clear-cache
```

后台生成使用现有 `default` 队列，任务超时 600 秒。`attendance_voice_queue` 仅供隔离测试站点覆盖队列；自定义队列必须同时配置并启动对应 worker。

宿主服务通过固定 Compose 文件管理引擎；Web 容器没有 Docker socket。本站安装路径已写入 [用户服务模板](../deploy/hrms-attendance-voice-engines.service)，在服务器主机以 `uo` 用户执行：

```bash
mkdir -p ~/.config/systemd/user
cp deploy/hrms-attendance-voice-engines.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hrms-attendance-voice-engines.service
systemctl --user status hrms-attendance-voice-engines.service
```

用户服务应配置开机驻留（本站 `uo` 已启用 linger）。部署到其他路径时修改模板中的路径；Docker 网络默认 `docker_default`，可通过服务的 `NEMO_NETWORK` 环境变量覆盖。

两种引擎均优先 GPU，只有加载音色、试听或生成时启动；空闲 60 秒停止并释放模型占用。小型租约管理进程常驻，预生成音频一直保留，日常打卡不启动 TTS。NVIDIA runtime 不可用时，可停止该服务，给 `ExecStart` 添加 `--cpu` 后重新加载并启动；CPU 与 GPU 模式不可同时运行。

查看运行情况：

```bash
journalctl --user -u hrms-attendance-voice-engines.service -n 50 --no-pager
docker compose -f deploy/attendance-voice.compose.yaml --profile gpu ps -a
```

草稿、预览和待发布资源位于 `sites/hrms.localhost/private/attendance-voice-settings/`；正式资源仍位于 `private/attendance-sign/`，设备接口保持 v1。备份这两个私有目录即可保留设置与发布内容，不要把员工读音或站点凭据提交到 Git。

2026-10-17 上线管理页时保留原正式发布内容，不自动替换全名语音。用户在页面填写姓氏假名、试听满意后，自行生成和发布首个姓氏版本。

## 初版上线验证记录（旧16k，历史）

2026-10-17：37 项相关测试通过，隔离站点真实浏览器走通修改姓氏假名、试听、后台生成及手动发布；桌面和 375px 布局检查通过。独立代码审查使用 `gpt-6-luna / medium`，无剩余重要问题。

正式站点管理员页面可打开，显示全部 28 名在职员工；普通 VOICEVOX 提供 43 个角色、127 种说话风格。真实 GPU 试听为 mono PCM16 / 16kHz，样音约 2.07 秒；引擎日志确认使用 CUDA，空闲后容器自动停止。访客访问设置及预览音频均返回 403。原设备事件与现有 WAV 接口返回 200，WAV 哈希校验通过。正式草稿仍为初始 revision 0，已发布 manifest 与上线前一致。


## 24kHz 升级验证（2026-10-17）

试听、网页生成、CSV生成和新资源发布校验已统一为24000Hz、PCM16、单声道、最长5秒，完整WAV上限262144字节。43项相关测试通过，包含完整5秒、超1帧、截断、旧格式拒绝与旧正式资源可读。普通VOICEVOX和Nemo均已真实GPU合成验证24k输出。

正式公网试听返回24k音频；默认后台队列已按当时保存的No.7音色生成28人、56段映射（44个去重文件），全部24k且在5秒内，处于待发布状态。未更改员工读音、音色/语速草稿或正式manifest；现有设备事件与旧WAV接口保持200。用户在本机固件验证后自行发布，后续草稿变化需重新生成。固件调整与新样音见[24k交接说明](attendance-sign-24khz-firmware-handoff.md)。
