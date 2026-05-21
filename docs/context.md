# 项目核心上下文 (Project Context)

本文件用于记录“1.54寸太空人天气时钟天气预警站”项目的核心硬件环境、引脚定义、编译烧录指南及关键改动日志，以便后续维护。

---

## 一、 开发环境搭建与初始化 (Environment Setup)
为了在另外一台电脑上快速初始化编译环境，请确保系统已安装 [arduino-cli](https://arduino.github.io/arduino-cli/)。

### 1. 手动步骤
在一台新电脑上，依次执行以下命令：
```bash
# 1. 配置 ESP32 开发板源地址 (如已配置可跳过)
arduino-cli config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

# 2. 更新开发板索引
arduino-cli core update-index

# 3. 安装指定版本 2.0.17 的 ESP32 核心包 (必须对齐版本，防止新版本 API 兼容问题)
arduino-cli core install esp32:esp32@2.0.17
```

### 2. 一键脚本初始化
项目根目录下提供了一键初始化脚本 `init_env.sh`。在新电脑上只需运行：
```bash
chmod +x init_env.sh
./init_env.sh
```

---

## 二、 硬件引脚映射 (Wiring Definition)
依据本地 `libraries/TFT_eSPI/User_Setup.h` 的实际配置，物理接线映射如下：

| 屏幕引脚 | 功能说明 | 对应 ESP32-C3 GPIO 编号 |
| :--- | :--- | :--- |
| **GND** | 电源地 | GND |
| **VCC** | 3.3V 电源 | 3.3V |
| **SCL** | SPI 时钟 (SCLK) | GPIO 3 |
| **SDA** | SPI 数据输入 (MOSI) | GPIO 5 |
| **DC** | 数据/命令控制引脚 | GPIO 2 |
| **RES** | 复位引脚 (RST) | GPIO 6 |
| **BLK** | 背光控制引脚 (BL) | GPIO 1 |
| **CS** | 片选引脚 | 未物理连接 (软定义为 -1) |

---

## 三、 编译与烧录指南
- **开发板 FQBN**：`esp32:esp32:esp32c3`
- **分区配置**：需指定 `PartitionScheme=huge_app`（本程序固件较大，超过默认 1.2MB 限制）
- **编译烧录一体化命令**：
  ```bash
  arduino-cli compile -u -p /dev/cu.usbmodem11201 -b esp32:esp32:esp32c3 --board-options "PartitionScheme=huge_app" --libraries "./libraries" "./SmallDesktopDisplay"
  ```

---

## 四、 关键改动日志 (Change Log)

### [2026-05-21] 修复 ESP32-C3 架构下初始化崩溃与无限闪屏重启
在将此 ESP32 项目迁移部署至 ESP32-C3 开发板时，遇到了芯片上电 269ms 立即发生 `Guru Meditation Store access fault` 崩溃重启并导致闪屏的问题。已进行如下修复：

1. **未接 CS 引脚的防越界安全校验**：
   - **修改位置**：[TFT_eSPI.cpp](file:///Users/rexchang/learn/python/v1.4加气象预警/libraries/TFT_eSPI/TFT_eSPI.cpp)
   - **问题原因**：CS 被宏定义为 `-1` 时，底层强行执行了 `pinMode(-1, OUTPUT)`，这在 ESP32 核心中导致了对 `255` 的越界读取与 `gpio_set_level(227)` 报错及内存非法写入。
   - **修复内容**：在涉及 `TFT_CS` 和 `TFT_RST` 的 `pinMode`、`digitalWrite` 初始化时，增设了 `if (pin >= 0)` 的正数合法性校验，避免了非法越界值传入底层核心。

2. **寄存器重映射（防主 Flash 寄存器被篡改）**：
   - **修改位置**：[TFT_eSPI_ESP32_C3.h](file:///Users/rexchang/learn/python/v1.4加气象预警/libraries/TFT_eSPI/Processors/TFT_eSPI_ESP32_C3.h)
   - **问题原因**：库中默认 `SPI_PORT` 设定为 `SPI2_HOST`（数值为 `1`），而在新的 ESP32-C3 Arduino Core 中，这会被错误解析至 `SPI1`（挂载芯片主 Flash 外设的主通道），在执行 `SET_BUS_WRITE_MODE` 指令解引用 `_spi_user` 指针写入时，破坏了 Flash 读取流导致 Panic 重启。
   - **修复内容**：将 `#define SPI_PORT SPI2_HOST` 修改为了强指引脚外设寄存器专用的 `#define SPI_PORT 2`，确保所有的 SPI 命令、数据和宽度寄存器指针都精确指向对 C3 芯片完全安全的物理 SPI2 总线。
