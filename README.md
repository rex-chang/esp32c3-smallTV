---
title: 1.54寸太空人天气时钟天气预警站
description: ESP32-C3 基于 Arduino 框架的 TFT 气象预警系统
---

# 1.54寸太空人天气时钟天气预警站

## 项目简介
本项目基于 **ESP32‑C3** 开发板，使用 **1.54寸 TFT LCD (ST7789)** 显示天气信息并提供气象预警。项目源码位于 `SmallDesktopDisplay/`，核心库已放在 `libraries/`。

## 硬件环境
| 组件 | 型号/说明 | 接口 | GPIO |
|------|-----------|------|------|
| MCU | ESP32‑C3 (RISC‑V) | — | — |
| 屏幕 | 金逸晨 1.54寸 TFT LCD (ST7789) | SPI | SCL: GPIO3, SDA: GPIO5, DC: GPIO2, RES: GPIO6, BLK: GPIO1 |
| 温湿度传感器 | DHT22 | — | — |
| LED 灯带 | WS2812B (FastLED) | — | — |

> **NOTE**: 硬件引脚映射可在 `docs/hardware.yaml` 中查看完整机器可读描述。

## 软件依赖
- Arduino CLI (`brew install arduino-cli`)
- ESP32 Arduino core (`arduino-cli core update-index && arduino-cli core install esp32:esp32`)
- 项目依赖库已放在 `libraries/`，通过 `arduino-cli compile` 时使用 `--libraries "./libraries"` 引入。

## 编译 & 烧录
```bash
# 连接开发板（示例为 /dev/cu.usbmodem11201）
arduino-cli compile -u -p /dev/cu.usbmodem11201 \
  -b esp32:esp32:esp32c3 \
  --board-options "PartitionScheme=huge_app" \
  --libraries "./libraries" "./SmallDesktopDisplay"
```

## 项目结构
```
.
├─ SmallDesktopDisplay/        # 主程序入口
│   └─ SmallDesktopDisplay.ino
├─ src/                       # 模块化代码
│   ├─ display.cpp / display.h
│   ├─ weather.cpp / weather.h
│   └─ alert.cpp   / alert.h
├─ libraries/                 # 第三方库
├─ docs/
│   ├─ context.md
│   └─ hardware.yaml          # 机器可读硬件配置
└─ README.md                  # 本文件
```

## AI 辅助脚本
项目提供 `scripts/generate_module.py`，可根据 Prompt 自动生成符合项目规范的模块代码（参考 `README` 中的使用示例）。

---

*本项目已使用 Git 进行版本管理，首次提交已完成。*
