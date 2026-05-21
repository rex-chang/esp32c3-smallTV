#!/bin/bash
# =================================================================
# 1.54寸气象预警太空人时钟 - 开发编译环境一键配置脚本
# 支持 OS: macOS / Linux
# =================================================================

set -e

echo "=========================================="
echo " 开始初始化 ESP32-C3 开发编译环境"
echo "=========================================="

# 1. 检查 arduino-cli
if ! command -v arduino-cli &> /dev/null; then
    echo "❌ 错误: 未检测到 arduino-cli 命令行工具！"
    echo "请先在您的电脑上安装 arduino-cli。"
    echo "  - macOS (Homebrew): brew install arduino-cli"
    echo "  - 其他平台请参考官网: https://arduino.github.io/arduino-cli/"
    exit 1
fi

# 2. 检查或生成配置文件，并添加 ESP32 官方板卡管理链接
echo "ℹ️  步骤 1: 配置 ESP32 板卡管理源..."
# 若无配置文件则初始化生成，支持源追加
if [ ! -f "$HOME/.arduino15/arduino-cli.yaml" ] && [ ! -f "$HOME/Library/Arduino15/arduino-cli.yaml" ]; then
    arduino-cli config init || true
fi

# 追加或重写 additional_urls 选项
arduino-cli config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
echo "✅ 板卡源配置完成。"

# 3. 更新板卡索引
echo "ℹ️  步骤 2: 正在更新开发板索引，请稍候..."
arduino-cli core update-index
echo "✅ 索引更新完成。"

# 4. 安装指定版本的 ESP32 核心包
echo "ℹ️  步骤 3: 正在安装 esp32:esp32@2.0.17 核心包..."
arduino-cli core install esp32:esp32@2.0.17
echo "✅ ESP32 核心包安装完成。"

echo "=========================================="
echo " 🎉 环境配置成功！"
echo " 您可以在本项目根目录下执行以下命令进行编译与烧录："
echo " arduino-cli compile -u -p <您的串口端口> -b esp32:esp32:esp32c3 --board-options \"PartitionScheme=huge_app\" --libraries \"./libraries\" \"./SmallDesktopDisplay\""
echo "=========================================="
