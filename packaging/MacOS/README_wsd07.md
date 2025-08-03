# Cura macOS 打包脚本 (wsd07 定制版)

这是一个专为 wsd07 开发环境定制的 Cura macOS 打包脚本，支持使用本地源代码和预编译的 CuraEngine 进行打包。

## 特性

✅ **本地源代码支持**: 使用本地 Cura 和 Uranium 源代码进行编译  
✅ **预编译 CuraEngine**: 使用预编译的 CuraEngine 可执行文件  
✅ **并行开发模式**: 支持 Cura 和 Uranium 的并行开发环境  
✅ **自动依赖管理**: 自动安装和配置所需的 Python 依赖  
✅ **智能文件收集**: 自动收集所有必要的资源和插件文件  
✅ **多格式输出**: 支持生成 DMG 和 PKG 安装包  
✅ **详细日志**: 提供详细的构建过程日志和错误诊断  

## 环境要求

### 必需组件
- **Python 3.8+**: 推荐使用 Python 3.12
- **虚拟环境**: 强烈推荐使用虚拟环境
- **Cura 源代码**: 本地 Cura 项目目录
- **Uranium 源代码**: 本地 Uranium 项目目录（与 Cura 同级）
- **预编译 CuraEngine**: CuraEngine.exe 文件位于 Cura 根目录

### 可选组件
- **create-dmg**: 用于创建 DMG 安装包 (`brew install create-dmg`)
- **代码签名证书**: 用于签名应用程序（可选）

## 目录结构

```
Cura-Dev/
├── Cura/                           # Cura 源代码
│   ├── CuraEngine.exe             # 预编译的 CuraEngine (必需)
│   ├── packaging/MacOS/
│   │   ├── build_macos_package_wsd07.py  # 主打包脚本
│   │   ├── build_example_wsd07.sh        # 示例脚本
│   │   └── README_wsd07.md              # 本文档
│   └── ...
└── Uranium/                        # Uranium 源代码 (与 Cura 同级)
    └── ...
```

## 快速开始

### 1. 基本使用

```bash
# 进入 Cura 项目目录
cd /path/to/Cura

# 激活虚拟环境（推荐）
source venv/bin/activate

# 运行示例脚本（最简单的方式）
./packaging/MacOS/build_example_wsd07.sh

# 或直接使用 Python 脚本
python3 packaging/MacOS/build_macos_package_wsd07.py \
    --dist-path ./dist \
    --cura-version 5.8.0 \
    --filename "UltiMaker-Cura-5.8.0-macOS-Custom" \
    --build-dmg
```

### 2. 高级用法

```bash
# 指定自定义路径
python3 packaging/MacOS/build_macos_package_wsd07.py \
    --cura-path /custom/path/to/Cura \
    --uranium-path /custom/path/to/Uranium \
    --dist-path ./output \
    --app-name "My-Custom-Cura" \
    --cura-version 5.8.0 \
    --filename "Custom-Cura-5.8.0-macOS" \
    --build-dmg \
    --build-pkg

# 只检查环境，不构建
./packaging/MacOS/build_example_wsd07.sh --check-only

# 同时生成 DMG 和 PKG
./packaging/MacOS/build_example_wsd07.sh --build-pkg
```

## 参数说明

### 主要参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--cura-path` | Cura 源代码路径 | 自动检测 |
| `--uranium-path` | Uranium 源代码路径 | 自动检测 |
| `--dist-path` | 输出目录 | 必需 |
| `--app-name` | 应用程序名称 | UltiMaker-Cura |
| `--cura-version` | Cura 版本号 | 必需 |
| `--filename` | 输出文件名（不含扩展名） | 必需 |

### 构建选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--build-dmg` | 构建 DMG 安装包 | True |
| `--build-pkg` | 构建 PKG 安装包 | False |

## 构建流程

1. **环境检查**: 验证 Python、虚拟环境、源代码路径等
2. **依赖安装**: 自动安装 PyInstaller 和其他必需的 Python 包
3. **开发模式安装**: 以开发模式安装 Uranium 和 Cura
4. **文件收集**: 收集所有必要的资源、插件和二进制文件
5. **PyInstaller 配置**: 生成定制的 PyInstaller 配置文件
6. **应用构建**: 使用 PyInstaller 构建 macOS 应用程序
7. **安装包创建**: 创建 DMG 和/或 PKG 安装包
8. **验证**: 检查构建结果和文件大小

## 输出文件

构建完成后，在指定的输出目录中会生成：

```
dist/
├── UltiMaker-Cura.app/                    # macOS 应用程序
├── UltiMaker-Cura-VERSION-macOS.dmg      # DMG 安装包
└── UltiMaker-Cura-VERSION-macOS.pkg      # PKG 安装包（可选）
```

## 故障排除

### 常见问题

#### 1. CuraEngine 未找到
```
❌ CuraEngine executable not found in Cura root directory
```
**解决方案**: 确保 `CuraEngine.exe` 文件位于 Cura 根目录下

#### 2. Uranium 路径错误
```
❌ Uranium root directory not found: /path/to/Uranium
```
**解决方案**: 确保 Uranium 项目与 Cura 项目在同一级目录下

#### 3. Python 依赖问题
```
❌ Failed to install package: ...
```
**解决方案**: 
- 确保使用虚拟环境
- 更新 pip: `pip install --upgrade pip`
- 手动安装失败的包

#### 4. PyInstaller 失败
```
❌ PyInstaller failed with return code 1
```
**解决方案**:
- 检查 PyInstaller 输出日志
- 确保所有依赖都已正确安装
- 尝试清理之前的构建: `rm -rf dist/build`

#### 5. 应用大小异常
```
⚠️ Warning: Application size seems unusually small/large
```
**解决方案**:
- 小于 50MB: 可能缺少资源文件，检查数据文件收集
- 大于 2GB: 可能包含不必要的文件，检查排除列表

### 调试技巧

1. **详细日志**: 脚本会自动显示详细的构建过程
2. **保留中间文件**: 构建失败时，检查 `dist/build` 目录
3. **手动测试**: 在构建前手动测试 Uranium 和 Cura 的导入
4. **虚拟环境**: 始终在干净的虚拟环境中构建

## 与官方脚本的区别

| 特性 | 官方脚本 | wsd07 定制版 |
|------|----------|-------------|
| 依赖管理 | Conan | pip + 开发模式 |
| CuraEngine | Conan 包 | 预编译文件 |
| Uranium | Conan 包 | 本地源代码 |
| 配置复杂度 | 高 | 低 |
| 开发友好性 | 中等 | 高 |
| 构建速度 | 慢 | 快 |

## 贡献

如果你发现问题或有改进建议，请：

1. 检查现有的故障排除指南
2. 提供详细的错误日志
3. 说明你的环境配置
4. 提出具体的改进建议

## 许可证

本脚本遵循与 Cura 相同的 LGPLv3 许可证。
