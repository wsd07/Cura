# 使用预编译的 CuraEngine.exe

## 概述

此配置已修改为使用预编译的 CuraEngine.exe 文件，而不是从源代码编译 CuraEngine。这样可以：

1. 避免 CuraEngine 编译过程中的复杂依赖问题
2. 加快构建速度
3. 使用稳定的预编译版本

## 文件放置位置

**重要：** 请将预编译的 `CuraEngine.exe` 文件放置在以下位置：

```
Cura/
├── CuraEngine.exe          # 预编译的 CuraEngine 可执行文件
├── conandata.yml
├── conanfile.py
└── ...其他文件
```

即：**将 `CuraEngine.exe` 直接放在 Cura 项目的根目录下**

## 获取预编译的 CuraEngine.exe

你可以通过以下方式获取预编译的 CuraEngine.exe：

1. **从官方发布版本提取**：
   - 下载官方 Cura 安装包
   - 安装后从安装目录复制 `CuraEngine.exe`
   - 通常位于：`C:\Program Files\UltiMaker Cura 5.x\CuraEngine.exe`

2. **从之前的构建中保存**：
   - 如果你之前成功构建过 CuraEngine，可以保存该文件重复使用

3. **从其他开发环境复制**：
   - 如果你有其他能够成功编译 CuraEngine 的环境

## 构建流程变化

修改后的构建流程：

1. **依赖安装**：跳过 CuraEngine 包，只安装其他必要依赖
2. **Cura 应用构建**：使用 PyInstaller 创建 Cura 应用分发包
3. **CuraEngine 复制**：将预编译的 `CuraEngine.exe` 复制到分发包中
4. **安装包创建**：创建最终的 Windows 安装包

## 验证

构建过程中会检查 `CuraEngine.exe` 是否存在：

- ✅ 如果找到文件，会显示 "Found precompiled CuraEngine.exe, copying to distribution"
- ❌ 如果未找到文件，构建会失败并显示错误信息

## 注意事项

1. **版本兼容性**：确保 CuraEngine.exe 版本与 Cura 版本兼容
2. **架构匹配**：确保 CuraEngine.exe 是 64 位版本（x64）
3. **文件权限**：确保文件具有执行权限
4. **Git 管理**：建议将 `CuraEngine.exe` 添加到 `.gitignore` 中，避免提交大型二进制文件到版本控制

## 恢复编译模式

如果将来想要恢复从源代码编译 CuraEngine，可以：

1. 在 `conandata.yml` 中取消注释 CuraEngine 依赖
2. 注释掉 binaries 部分的 CuraEngine 配置
3. 移除 GitHub Actions 中的 "Copy precompiled CuraEngine.exe" 步骤
