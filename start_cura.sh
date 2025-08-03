#!/bin/bash

# Cura 开发环境启动脚本
# 使用方法: ./start_cura.sh

echo "启动 Cura 开发环境..."

# 检查是否在正确的目录
if [ ! -f "cura_app.py" ]; then
    echo "错误: 请在 Cura 根目录下运行此脚本"
    exit 1
fi

# 检查 CuraEngine 符号链接
if [ ! -L "CuraEngine" ]; then
    echo "创建 CuraEngine 符号链接..."
    ln -sf ../CuraEngine/CuraEngine CuraEngine
fi

# 检查虚拟环境
if [ ! -f "build/generators/virtual_python_env.sh" ]; then
    echo "错误: 虚拟环境未找到，请先运行 conan install"
    exit 1
fi

# 激活虚拟环境并启动 Cura
echo "激活虚拟环境并启动 Cura..."
source build/generators/virtual_python_env.sh && python cura_app.py

echo "Cura 已退出"
