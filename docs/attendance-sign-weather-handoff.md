# 可直接发给本机 Codex：板端天气 API

请在现有 ESP32-S3-RLCD-4.2 签到牌固件中增加低频天气显示。服务端复用PWA现有WeatherAPI.com天气源，板子只调用HRMS，不持有第三方API密钥，也无需请求第三方天气图片。

正式服务端已于2026-10-17部署，日语真实天气及公网设备鉴权验证通过；本机仍需完成固件接入、烧录与真屏验收。

接口沿用同一HTTPS地址、地点和设备密钥，不改变动态二维码120秒周期、成功事件每秒轮询、姓名反馈和24k语音。说明与 `attendance-sign-weather-handoff.zip` 一起转发，包内包含本说明及ok/stale/unavailable虚构JSON样例。

## 请求

```text
GET https://erphr.toiroworld.com/api/method/hrms.api.attendance_sign.get_weather?location=uo-2f-door
X-Attendance-Sign-Key: 沿用本机私有配置
User-Agent: UO-Attendance-Sign/1.0 (ESP32-S3)
```

- 只支持GET；不需要员工登录会话。即使网页二维码免展示密钥，天气接口仍必须带真实设备密钥，缺失/错误/地点不存在或禁用返回403。
- 天气描述统一日语，`locale` 固定为 `ja-JP`，无需传语言参数。密钥不拼URL，不写入提交或普通日志。
- **天气地点沿用PWA的固定坐标 `34.66497,135.15820`**。`location` 是设备鉴权用的打卡点，不表示按各地点GPS、板子IP或手机位置重新选择天气城市。

## 响应字段

响应保留Frappe `message` 包装。示例数值是虚构数据：

```json
{
  "message": {
    "version": 1,
    "locale": "ja-JP",
    "location": "uo-2f-door",
    "server_time": 1792206020,
    "timezone": "Asia/Tokyo",
    "provider": "WeatherAPI.com",
    "status": "ok",
    "date": "2026-10-17",
    "fetched_at": 1792206000,
    "refresh_after": 580,
    "weather": {
      "temp_c": 23.5,
      "maxtemp_c": 26,
      "mintemp_c": 19,
      "condition_text": "晴れ",
      "icon_key": "clear",
      "is_day": true
    }
  }
}
```

| 字段 | 含义 |
| --- | --- |
| `version` | 当前协议为1 |
| `locale` | 固定ja-JP，天气文字为日语 |
| `server_time` | 生成本次响应的Unix秒 |
| `status` | ok为正常；stale为暂用旧数据；unavailable为无可用天气 |
| `date` | 服务器站点当天日期，高低温对应PWA的今天预报 |
| `fetched_at` | 最后成功从PWA天气源取得数据的Unix秒；**不是第三方气象观测时刻**；无数据为null |
| `refresh_after` | 距离下次适合获取天气的秒数，按本地单调计时器安排；不是二维码刷新周期 |
| `weather.temp_c` | 当前温度（摄氏度），可能为0或负数 |
| `maxtemp_c` / `mintemp_c` | 今日高低温，可单独为null，未知时显示“--”而非0 |
| `condition_text` | 同源天气文字，可截断/换行显示，不依靠固定emoji猜天气 |
| `icon_key` | 给板子本地黑白图标用的简化天气类别，不是WeatherAPI原生condition.code |
| `is_day` | 从PWA图标路径识别昼夜，true/false；无法识别为null |

`weather` 在unavailable时为null，`fetched_at` 也为null；HTTP200不代表一定有天气数据。错误响应不下发供应商URL、密钥或异常详情。

## 黑白图标

| icon_key | 推荐显示 |
| --- | --- |
| clear | is_day=true画太阳，false画月亮，null用通用晴天符号 |
| partly_cloudy | 少云，根据昼夜选日/月与云组合 |
| cloudy | 多云/阴天的云图形 |
| fog | 雾/薄雾 |
| rain | 雨/毛毛雨/冻雨 |
| snow | 雪/暴风雪 |
| sleet | 雨夹雪/冰粒 |
| thunder | 雷暴，可配合天气文字表示雨雪细节 |
| unknown | 通用天气标识或仅显示文字，不能当作晴天 |

映射参考 [WeatherAPI官方图标表](https://www.weatherapi.com/docs/weather-icons/)；服务端离线映射，板子不需要定时下载该表或彩色PNG。未知的新图标仍保留文字。

## 缓存、失败和调度

- 服务器成功数据缓存10分钟，按站点和日期隔离，多次读取不会每次都请求第三方。`refresh_after` 会按缓存剩余时间递减，正常范围1～600秒；按返回值安排天气任务即可。
- 天气源短暂失败时返回同日、不超过1小时的最近成功数据并标记 `stale`，建议显示“更新延迟”及最后获取时间；失败阶段每60秒重试。超过1小时或跨日不拿旧高低温冒充今天，返回unavailable。
- unavailable时天气位置显示“天气暂不可用”或“--”，不要显示0℃晴天。清除过旧图标，但继续二维码显示、事件轮询及播报。
- 网络错误/HTTP5xx/解析错误也只影响天气区域，约60秒后再试；403检查设备配置，不要高频重试。
- 冷缓存会调用现有天气源（其上游超时为5秒），板端天气请求可给约8秒超时，并在独立任务执行，不阻塞UI、二维码换码、音频或事件轮询。

## 本机实施与验收

1. 在实际目标板工程里沿用已有HTTPS客户端/证书和设备私有配置，新增天气GET及上述字段解析；不要为了天气更换ESP-IDF/LVGL版本。
2. 天气放在顶部或既有空闲区域，保持二维码的位置、尺寸和白边固定。天气长文字应截断或换行，不能挤压或遮住二维码；打卡成功反馈仍按原队列显示。
3. 本地使用包内三个虚构JSON验证正常、旧数据提示及缺数据；补测0度、负温、缺高低温、未知图标和昼夜切换。核对 `date` 是今天再显示今日高低温。
4. 使用真实接口验证日语天气、取数与缓存提示。不要向第三方发送员工姓名、员工ID或设备密钥。
5. 同时验证扫码、换码、连续姓名反馈和24k播放正常；天气服务断网/恢复时二维码流程不受影响。
6. 报告修改工程、固件commit、实际字段和真屏结果。服务器API通过不代表已经完成本机烧录与显示验收。

数据来源为WeatherAPI.com，可在天气详情或设备说明中保留来源文字。若委派代码审查，按用户要求显式使用 `model="gpt-6-luna"`、`reasoning_effort="medium"`。
