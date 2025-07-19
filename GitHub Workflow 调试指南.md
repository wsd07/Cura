# GitHub Workflow 调试指南

## 概述

本文档详细说明了Cura项目的GitHub Actions CI/CD工作流程，包括运行逻辑、关键配置和针对性修改。

## 目录

1. [工作流架构](#工作流架构)
2. [核心文件说明](#核心文件说明)
3. [构建流程详解](#构建流程详解)
4. [环境兼容性设计](#环境兼容性设计)
5. [关键修改说明](#关键修改说明)
6. [调试技巧](#调试技巧)
7. [常见问题解决](#常见问题解决)

## 工作流架构

### 主要工作流文件

```
.github/workflows/
├── windows.yml                    # Windows安装程序构建入口
├── cura-installer-windows.yml     # Windows安装程序构建实现
├── cura-installer-linux.yml       # Linux安装程序构建
├── cura-installer-macos.yml       # macOS安装程序构建
└── cura-installers.yml           # 多平台安装程序构建
```

### 工作流调用关系

```
windows.yml (手动触发)
    └── cura-installer-windows.yml (被调用)
        └── setup-build-environment (Action)
        └── set-package-overrides (Action)
```

## 核心文件说明

### 1. conanfile.py

**功能**：Conan包管理器的配置文件，定义了Cura的依赖关系和构建逻辑。

**关键特性**：
- 支持多平台构建（Windows、macOS、Linux）
- 动态依赖包选择（根据运行环境）
- PyInstaller集成
- 许可证管理

**环境适配逻辑**：
```python
# 根据环境变量检测运行环境
is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

# GitHub Actions环境使用官方包
if is_github_actions:
    self.requires("uranium/5.11.0-alpha.0@ultimaker/testing")
# 本地macOS环境使用自定义包
else:
    self.requires("uranium/5.11.0@wsd07/testing")
```

### 2. conandata.yml

**功能**：Conan数据配置文件，定义版本、依赖包、PyInstaller配置等。

**关键配置**：
- `requirements`: 核心依赖包列表
- `pyinstaller`: PyInstaller打包配置
- `urls`: API端点配置（生产/测试环境）

### 3. cura-installer-windows.yml

**功能**：Windows平台安装程序构建的核心工作流。

**构建阶段**：
1. **环境设置** - 安装Python、Conan、系统依赖
2. **包收集** - 下载和构建所有依赖包
3. **分发创建** - 使用PyInstaller创建可执行文件
4. **安装程序生成** - 创建EXE和MSI安装程序
5. **文件上传** - 上传构建产物

## 构建流程详解

### 阶段1：环境准备

```yaml
- name: Setup the build environment
  uses: wsd07/Cura/.github/actions/setup-build-environment@main
  with:
    install_system_dependencies: true
    repository_path: _cura_sources
    python_set_env_vars: false
```

**执行内容**：
- 安装Python 3.12.2
- 安装Conan 2.7.0
- 检出Cura源代码到`_cura_sources`目录
- 配置构建环境变量

### 阶段2：依赖包管理

```powershell
conan install . --build=missing --update -g VirtualPythonEnv -of ../cura_inst --deployer-package=*
```

**参数说明**：
- `--build=missing`: 构建缺失的包
- `--update`: 更新包到最新版本
- `-g VirtualPythonEnv`: 生成虚拟Python环境
- `-of ../cura_inst`: 输出到cura_inst目录
- `--deployer-package=*`: 部署所有包

### 阶段3：PyInstaller打包

```cmd
call cura_inst\build\generators\conanrun.bat && python cura_inst\UltiMaker-Cura.spec
```

**功能**：
- 激活Conan虚拟环境
- 执行PyInstaller规格文件
- 生成独立的可执行文件

### 阶段4：安装程序创建

**EXE安装程序**：
```powershell
python ..\cura_inst\packaging\NSIS\create_windows_installer.py
```

**MSI安装程序**：
```powershell
python ..\cura_inst\packaging\msi\create_windows_msi.py
```

## 环境兼容性设计

### 双环境支持策略

本项目设计为同时支持两种开发环境：

1. **GitHub Actions环境**
   - 使用官方Ultimaker依赖包
   - 跳过许可证下载（节省时间）
   - 使用预编译CuraEngine.exe

2. **本地macOS环境**
   - 使用自定义wsd07依赖包
   - 完整许可证下载
   - 从依赖包构建CuraEngine

### 环境检测机制

```python
# 在conanfile.py中的环境检测
is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"

# 根据环境调整配置
"skip_licenses_download": os.environ.get("GITHUB_ACTIONS") == "true"
```

## 关键修改说明

### 1. PowerShell语法修复

**问题**：PowerShell变量后跟冒号的语法错误
```powershell
# ❌ 错误语法
Write-Host "Available MSVC versions in $MSDIR:"

# ✅ 正确语法
Write-Host "Available MSVC versions in ${MSDIR}:"
```

### 2. MSVC Redistributables处理

**功能**：自动查找和复制Visual Studio运行时库
```powershell
# 支持多个VS版本
$VS_PATHS = @(
  "C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Redist/MSVC",
  "C:/Program Files/Microsoft Visual Studio/2022/Professional/VC/Redist/MSVC",
  "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Redist/MSVC"
)
```

### 3. 预编译CuraEngine集成

**GitHub Actions环境**：
```yaml
- name: Copy precompiled CuraEngine.exe
  run: |
    copy CuraEngine.exe dist/UltiMaker-Cura/.
```

**本地环境**：通过Conan依赖包自动处理

### 4. 动态依赖包选择

**实现逻辑**：
```python
def requirements(self):
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    
    if is_github_actions:
        # GitHub环境使用官方包
        self.requires("uranium/5.11.0-alpha.0@ultimaker/testing")
    else:
        # 本地环境使用自定义包
        self.requires("uranium/5.11.0@wsd07/testing")
```

## 调试技巧

### 1. 启用详细日志

在workflow中添加调试输出：
```yaml
- name: Debug step
  run: |
    echo "Current directory: $(pwd)"
    echo "Environment variables:"
    env | sort
    echo "File listing:"
    ls -la
```

### 2. 检查构建产物

```powershell
Write-Host "Checking generated files:"
if (Test-Path "cura_inst") {
    Get-ChildItem "cura_inst" -Recurse | Select-Object FullName, Length
}
```

### 3. 验证依赖包

```bash
conan list "*" --format=json
```

## 常见问题解决

### 1. Conan包解析失败

**症状**：`ERROR: Package 'xxx' not found`

**解决方案**：
- 检查包名和版本号
- 验证Conan远程仓库配置
- 确认包在指定仓库中存在

### 2. PyInstaller打包失败

**症状**：`ModuleNotFoundError` 或缺失依赖

**解决方案**：
- 检查`hiddenimports`配置
- 验证虚拟环境激活
- 添加缺失的模块到`collect_all`

### 3. 安装程序创建失败

**症状**：NSIS或MSI构建错误

**解决方案**：
- 检查所需文件是否存在
- 验证路径配置
- 确认签名证书配置

### 4. 权限问题

**症状**：文件访问被拒绝

**解决方案**：
- 检查文件权限
- 使用管理员权限运行
- 验证防病毒软件设置

## 维护建议

1. **定期更新依赖**：保持Conan包和Python依赖的最新版本
2. **监控构建时间**：优化缓存策略以减少构建时间
3. **测试多环境**：确保本地和CI环境的一致性
4. **文档同步**：及时更新文档以反映配置变更

## 联系信息

如有问题或建议，请通过以下方式联系：
- GitHub Issues
- 项目维护者邮箱

---

*最后更新：2025年7月19日*
