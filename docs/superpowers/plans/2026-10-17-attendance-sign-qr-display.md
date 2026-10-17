# 板端动态二维码与120秒换码实施计划

> 使用 superpowers:executing-plans 当前会话直接实施；最终代码审查gpt-6-luna / medium。

**Goal:** 服务端支持板子显示与网页相同的动态打卡码，uo-2f-door换码改为120秒，并交付本机实施说明。
**Architecture:** 网页、公开取码API和板端取码API共用签名/时槽/截止时间；每地点使用自身qr_refresh_interval（默认30），签名校验同步同一周期。板端新增GET get_qr，复用现有X-Attendance-Sign-Key强制鉴权，原get_events/get_audio v1不变。
**Tech Stack:** 现有Frappe/Python；本机ESP32固件由本机Codex完成。
**Spec:** 用户已批准“二维码常驻＋底部姓名反馈＋原语音播报”，并明确服务端换码周期由30秒改为2分钟。

## Global Constraints

只把正式uo-2f-door配置改120，其余地点按各自配置。保持原当前＋上一时槽校验规则（120秒一轮，单码最长约240秒）；返回refresh_at/expires_at，不让板子猜有效期。签名密钥只留服务器，展示密钥仅请求头；不改手机PWA/打卡业务校验、不在正式站点伪造打卡。保留所有无关未提交工作、语音设置和已发布资源。

## Review Focus

网页首屏与API签名一致；120秒内部不能30秒提前失效；换码边界/旧码过期；地点间隔不能串用；板端无密钥/错误/跨地点/禁用一律403且不缓存；生成二维码不得创建考勤记录。

### Task 1: 时槽与校验

Files: 新hrms/utils/attendance_qr.py，hrms/api/qr_attendance.py，hrms/www/qr_display.py；hrms/tests/test_qr_attendance.py和相关扫码回归。
- [x] RED: 120秒同槽、119/120边界、截止时间，网页/API同码，120码校验到业务后续、上一时槽接受与过期拒绝、其他30秒地点正常。
- [x] 提取共用构建函数，生成与校验使用地点周期，网页首屏复用；相关测试转绿。

### Task 2: 板端接口与交接

Files: hrms/api/attendance_sign.py，hrms/tests/test_attendance_sign.py；新增docs/attendance-sign-qr-display-handoff.md及虚构示例JSON。
- [x] RED→GREEN: 设备GET get_qr(location)，始终校验真实设备密钥、地点和启用状态，返回version/locale/token/location/description/server_time/expires_in/refresh_at/expires_at，不缓存。
- [x] 文档明确300×400常驻码、QR原始内容/白边/整数像素、计时/断线/过期隐藏、原事件队列和24k播报并行，以及真实扫码验收；样包不含签名密钥/展示密钥/真实员工记录。
- [ ] 最终review、相关测试、限定文件合入部署；仅目标地点更新120并验证正式网页/旧API/新API一致，原配置及音频不变；交付可直接转发的ZIP。
