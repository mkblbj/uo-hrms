# 板端天气API实施计划

> 当前会话用superpowers:executing-plans直接实施；最终review为gpt-6-luna / medium。

**Goal:** 板子用现有设备密钥读取与PWA同源的当前天气、今日高低温及黑白图标代号。
**Architecture:** 新GET attendance_sign.get_weather(location,lang=ja)复用设备鉴权；新attendance_sign_weather服务调用既有hrms.api.get_weather_data，不修改其他任务正在改动的api/__init__.py或PWA。按站点/语言/当天缓存10分钟，失败每分钟重试，可标记使用同日最近1小时的旧数据；无可用数据返回明确unavailable。
**Tech Stack:** Frappe/Python、既有WeatherAPI.com源、现有Redis缓存。
**Spec:** 用户要求整理当前天气成板端API，以显示天气；引用任务已读取，当前PWA固定34.66497,135.15820，不按设备GPS/打卡地点切换天气城市。

## Global Constraints

不泄漏WeatherAPI密钥、不向板子下发第三方调用地址；不改PWA返回结构/天气配置及无关未提交文件；不影响二维码120秒、事件1秒和24k语音。默认ja，保留源已有ja/zh/en能力；fetched_at仅是服务端获取时间，不伪称气象观测时间。

## Review Focus

设备无/错/跨地点key与禁用地点在调用源前403；0度/负温有效；缺数据不伪造0度；文字和图标同源且支持昼夜/未知图标；缓存按语言及日期隔离；同日旧数据显式stale，跨日/过旧不冒充今天；错误不泄漏密钥/URL；语言上下文恢复。

### Task 1: 天气整理与缓存

Files: 新hrms/utils/attendance_sign_weather.py, 新hrms/tests/test_attendance_sign_weather.py。
- [x] RED→GREEN: 温度/高低温/天气文字，图标分组与昼夜/未知；真实Redis成功缓存及语言/日期隔离；失败stale/unavailable及过旧拒绝；语言上下文失败也恢复。
- [x] 实现复用源、有限字段规范化、官方图标ID离线映射、10分钟缓存和60秒失败重试，不新增第三方实时请求链。

### Task 2: API、文档与上线

Files: hrms/api/attendance_sign.py, hrms/tests/test_attendance_sign.py；新增docs/attendance-sign-weather-handoff.md。
- [x] RED→GREEN: 设备鉴权、schema、不缓存HTTP响应但复用服务端缓存、只读不写考勤。
- [x] 给本机API字段、状态和轮询提示、文字/黑白图标映射、未知/暂不可用、不得遮二维码、同源固定坐标的接入说明和虚构JSON样例。
- [ ] 相关检查、独立review、限定文件部署；真实源/公网/缓存与原QR/事件/语音验证，保留原文件与配置；交付可直接发本机的接口说明及ZIP。
