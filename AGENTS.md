# AGENTS.md — 1.54寸太空人天气时钟天气预警站 (SDD V1.4)

> 本文件面向 AI 编程助手。项目所有注释和文档均以中文为主，代码中变量名混合使用中英文。

---

## 项目概述

本项目是一个基于 **ESP32-C3** 的物联网小型桌面天气时钟显示器。设备通过 1.54 寸 TFT LCD 屏幕实时显示：

- 大型数字时钟（时/分/秒）
- 当前天气状况（温度、湿度、天气图标）
- 空气质量指数（PM2.5 / AQI）
- **气象预警信息**（天气预警等级与类型）
- 滚动天气信息横幅
- 动画太空人（"太空人"）角色

**原作**：Misaka  
**修改**：微车游  
**版本**：SDD V1.4  
**硬件平台**：ESP32-C3 (RISC-V 架构)

---

## 硬件配置

### 核心器件

| 器件 | 型号/规格 |
|------|----------|
| MCU | ESP32-C3 (RISC-V) |
| 显示屏 | 金逸晨 1.54寸 TFT LCD，ST7789 驱动，240×240 分辨率 |
| 可选传感器 | DHT11 温湿度传感器（GPIO 12） |

### 引脚映射

引脚定义在 `libraries/TFT_eSPI/User_Setup.h` 中配置：

| 屏幕引脚 | 功能 | ESP32-C3 GPIO |
|---------|------|--------------|
| GND | 电源地 | GND |
| VCC | 3.3V 电源 | 3.3V |
| SCL | SPI 时钟 (SCLK) | GPIO 3 |
| SDA | SPI 数据输入 (MOSI) | GPIO 5 |
| DC | 数据/命令控制 | GPIO 2 |
| RES | 复位引脚 (RST) | GPIO 6 |
| BLK | 背光控制引脚 (BL) | GPIO 1 |
| CS | 片选引脚 | **未物理连接**（软定义为 `-1`） |

> ⚠️ **重要**：CS 引脚未物理连接，在代码中定义为 `-1`。这导致了对 `TFT_eSPI` 库的特定修改（见下方"关键补丁"）。

---

## 技术栈

### 核心框架
- **Arduino**（ESP32 Arduino Core）

### 依赖库（全部 vendored 在 `/libraries/`）

| 库 | 用途 | 备注 |
|---|------|------|
| **TFT_eSPI** | ST7789 显示驱动 | 已针对 ESP32-C3 做关键补丁 |
| **TJpg_Decoder** | JPEG 图像解码 | 用于渲染嵌入式图片 |
| **ArduinoJson** | JSON 解析 | 解析天气 API 响应 |
| **Time-Library** | NTP 时间同步 | 中国时区 (UTC+8) |
| **WiFiManager** | Web 配网门户 | 首次启动时创建 AP 配网 |
| **DHT_sensor_library** | DHT11 传感器支持 | 可选，默认关闭 |
| **Adafruit_Unified_Sensor** | 传感器抽象层 | DHT 依赖 |
| **FastLED** | LED 控制 | 已包含但未使用 |

---

## 代码组织结构

```
SmallDesktopDisplay/
├── SmallDesktopDisplay.ino   # 主程序（1670 行）— 应用逻辑、WiFi、NTP、天气 API、Web 服务器
├── number.h / number.cpp     # Number 类 — 大型数字时钟渲染（36×60 白/橙，18×30 白）
├── weathernum.h / weathernum.cpp  # WeatherNum 类 — 天气图标映射渲染
├── qr.h                      # QR 码位图数据（PROGMEM 数组，当前未使用）
├── wd.h                      # 开机画面（240×240 RGB565，从 smart_New.JPG 生成）
├── smart_New.JPG             # 开机画面源图
├── bootloader.bin            # 预编译 bootloader
├── font/                     # 数字字体资源（30 个 .h 文件）
│   ├── O_3660_i0.h ~ O_3660_i9.h   # 橙色 36×60 数字 0-9
│   ├── W_3660_i0.h ~ W_3660_i9.h   # 白色 36×60 数字 0-9
│   ├── W_1830_i0.h ~ W_1830_i9.h   # 白色 18×30 数字 0-9
│   └── ZdyLwFont_20.h              # 中文字体（约 1.2MB）
└── img/                      # 图片资源
    ├── misaka.h / misaka111.h      # 角色图片
    ├── temperature.h / humidity.h  # 温湿度图标（JPEG PROGMEM）
    ├── pangzi/                     # 太空人动画帧 i0.h ~ i9.h
    ├── pangzi_change/              # 备用太空人帧
    └── tianqi/                     # 天气状况图标 t0.h ~ t99.h
```

### 主要模块说明

| 文件 | 行数 | 职责 |
|------|------|------|
| `SmallDesktopDisplay.ino` | 1670 | 主应用：WiFi 管理、NTP 同步、天气数据获取与解析、Web 服务器、显示刷新、串口命令处理 |
| `number.cpp/h` | 127/53 | `Number` 类：使用嵌入式 JPEG 字体渲染大型时钟数字 |
| `weathernum.cpp/h` | 101/41 | `WeatherNum` 类：将天气状况代码映射到对应图标图片 |

---

## 构建与烧录

### 构建工具链
- **工具**：`arduino-cli`
- **环境**：macOS（项目在此环境下开发验证）

### 构建命令

```bash
arduino-cli compile -u -p /dev/cu.usbmodem11201 \
  -b esp32:esp32:esp32c3 \
  --board-options "PartitionScheme=huge_app" \
  --libraries "./libraries" \
  "./SmallDesktopDisplay"
```

### 构建参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| FQBN | `esp32:esp32:esp32c3` | ESP32-C3 开发板 |
| PartitionScheme | `huge_app` | **必须指定** — 固件超过默认 1.2MB 限制 |
| 串口 | `/dev/cu.usbmodem11201` | macOS 下的设备串口（Linux 下通常为 `/dev/ttyUSB0`） |
| `-u` | — | 编译后自动上传（upload） |

### 构建产物（`/build_out/`）

| 文件 | 大小 | 用途 |
|------|------|------|
| `SmallDesktopDisplay.ino.bin` | ~1.5MB | 主固件 |
| `SmallDesktopDisplay.ino.bootloader.bin` | ~13KB | Bootloader |
| `SmallDesktopDisplay.ino.partitions.bin` | ~3KB | 分区表 |
| `SmallDesktopDisplay.ino.elf` | ~19MB | ELF 调试文件 |
| `SmallDesktopDisplay.ino.map` | ~12MB | 符号映射表 |

---

## 功能特性与编译开关

代码使用 `#define` 宏进行功能开关控制：

| 宏 | 默认值 | 说明 |
|---|--------|------|
| `BOARD_ESP32` | 已定义 | 目标平台为 ESP32（与 `BOARD_ESP8266` 互斥） |
| `WM_EN` | `1` | WiFiManager 配网门户使能 |
| `WebSever_EN` | `1` | Web 配置服务器使能（**注意拼写**：Sever 非 Server） |
| `DHT_EN` | `0` | DHT11 传感器支持（默认关闭） |
| `imgAst_EN` | `1` | 太空人动画显示 |

> 当 `WebSever_EN` 开启时，无法使用 WiFi 休眠功能（因为需要持续监听 HTTP 请求）。

---

## 配置与持久化

### EEPROM 地址映射

设置通过 EEPROM 持久化保存，断电不丢失：

| 地址 | 内容 | 默认值 |
|------|------|--------|
| 1 (`BL_addr`) | 背光亮度 (0-100) | 50 |
| 2 (`Ro_addr`) | 屏幕旋转方向 (0-3) | 0 |
| 3 (`DHT_addr`) | DHT 传感器使能标志 | 0 |
| 4 (`UpWeT_addr`) | 天气更新间隔（分钟） | 10 |
| 10 (`CC_addr`) | 城市代码 | 101280601（深圳） |
| 30 (`wifi_addr`) | WiFi SSID + 密码 | — |

### 屏幕旋转方向

| 值 | 方向 |
|----|------|
| 0 | USB 接口朝下 |
| 1 | USB 接口朝右 |
| 2 | USB 接口朝上 |
| 3 | USB 接口朝左 |

---

## 天气数据来源

| 接口 | URL |
|------|-----|
| 城市代码自动获取 | `http://wgeo.weather.com.cn/ip/?_={timestamp}` |
| 天气数据 | `http://d1.weather.com.cn/weather_index/{cityCode}.html` |
| NTP 服务器 | `ntp6.aliyun.com` |
| 时区 | UTC+8（中国标准时间） |

天气数据通过 HTTP GET 请求获取，响应体为 JavaScript 变量赋值形式，需通过字符串截取提取 JSON 片段。

---

## Web 配置界面

设备联网后可通过以下方式访问配置页面：
- mDNS 地址：`http://sd3.local`
- IP 地址：`http://{WiFi.localIP}`

支持配置的参数：城市代码、背光亮度、天气更新间隔、屏幕旋转方向、DHT 传感器开关。

---

## 串口调试

- **波特率**：115200（8/N/1）
- **命令格式**：输入十六进制代码控制

| 命令 | 功能 |
|------|------|
| `0x01` | 设置背光亮度（随后输入 0-100） |
| `0x02` | 设置城市代码（随后输入 9 位代码，0 表示自动） |
| `0x03` | 设置屏幕旋转方向（随后输入 0-3） |
| `0x04` | 设置天气更新间隔（随后输入 1-60 分钟） |
| `0x05` | 重置 WiFi 配置并重启设备 |
| `0x06` | 重启设备 |

---

## 关键补丁（ESP32-C3 兼容性修复）

在将项目从 ESP32 迁移到 ESP32-C3 时，对 `TFT_eSPI` 库进行了两处关键修改。这些修改已记录在 `docs/context.md` 中：

### 1. CS 引脚越界保护（`libraries/TFT_eSPI/TFT_eSPI.cpp`）

**问题**：CS 宏定义为 `-1` 时，`pinMode(-1, OUTPUT)` 导致 GPIO 越界访问，引发 `Guru Meditation` 崩溃。

**修复**：在所有涉及 `TFT_CS` 和 `TFT_RST` 的 `pinMode()` / `digitalWrite()` 调用前增加 `if (pin >= 0)` 校验。

### 2. SPI 端口寄存器重映射（`libraries/TFT_eSPI/Processors/TFT_eSPI_ESP32_C3.h`）

**问题**：默认 `#define SPI_PORT SPI2_HOST`（值为 `1`）在 ESP32-C3 Arduino Core 新版本中会被错误解析为 `SPI1`（主 Flash 总线），导致写入 SPI 寄存器时破坏 Flash 读取流，触发 Panic 重启。

**修复**：将定义改为 `#define SPI_PORT 2`，强制指向物理 SPI2 外设寄存器。

> ⚠️ **警告**：升级 `TFT_eSPI` 库时，上述两处修改会被覆盖，必须重新应用。

---

## 代码风格与约定

1. **注释语言**：代码注释以中文为主，变量名混合中英文（如 `updateweater_time`、`LCD_BL_PWM`、`Wifi_en`）。
2. **渲染模式**：使用 `TFT_eSprite` 进行离屏缓冲绘制，再通过 `pushSprite()` 推送至屏幕，最小化闪烁。
3. **图片存储**：所有图片以字节数组形式存储在 `PROGMEM`（Flash）中，通过 `TJpg_Decoder` 解码渲染。
4. **状态标志**：广泛使用全局变量作为状态标志（如 `Wifi_en`、`UpdateWeater_en`、`DHT_img_flag`）。
5. **字符串处理**：使用 Arduino `String` 类进行 HTTP 响应解析和 JSON 提取。

---

## 测试策略

本项目**没有自动化测试框架**。验证方式包括：

- **串口调试输出**：通过 115200 波特率串口监视器查看运行日志
- **视觉验证**：在 TFT 屏幕上观察显示效果
- **手动 Web 界面测试**：通过浏览器访问配置页面验证功能
- **加载动画**：`loading()` 函数在 WiFi 连接期间提供视觉反馈

---

## 部署/烧录流程

1. 连接 ESP32-C3 开发板至电脑 USB
2. 确认串口设备名称（macOS: `/dev/cu.usbmodem*`，Linux: `/dev/ttyUSB0`）
3. 执行编译烧录一体化命令（见"构建与烧录"章节）
4. 首次启动：
   - 设备自动创建 AP `AutoConnectAP`
   - 连接该 AP 后自动弹出配网页面（captive portal）
   - 配置 WiFi SSID、密码及其他参数
5. 后续启动：自动连接已保存的 WiFi，从 EEPROM 读取配置

---

## 安全注意事项

1. **WiFi 凭证明文存储**：SSID 和密码以明文形式存储在 EEPROM 中，无加密。
2. **HTTP 明文传输**：所有天气 API 请求使用 HTTP（非 HTTPS），存在中间人攻击风险。
3. **Web 服务器无认证**：配置页面 (`/`) 没有任何身份验证机制，局域网内任何设备均可访问和修改配置。
4. **串口命令无鉴权**：通过串口发送的 `0x05` 等命令可直接重置设备配置。
5. **EEPROM 写入寿命**：频繁修改配置会消耗 EEPROM 写入寿命（ESP32 闪存约 10 万次擦写）。
6. **CS=-1 的硬件风险**：虽然已通过软件补丁规避，但硬件上 CS 悬空可能在电磁干扰环境下导致显示异常。

---

## 文件清单速查

| 路径 | 说明 |
|------|------|
| `SmallDesktopDisplay/SmallDesktopDisplay.ino` | 主程序入口 |
| `SmallDesktopDisplay/number.cpp` | 大型数字渲染实现 |
| `SmallDesktopDisplay/weathernum.cpp` | 天气图标映射实现 |
| `libraries/TFT_eSPI/User_Setup.h` | 显示屏引脚与驱动配置 |
| `docs/context.md` | 硬件上下文与关键改动日志（中文） |
