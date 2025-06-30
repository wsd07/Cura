# Cura Translation Compilation

## 问题描述

当你在Cura中选择了简体中文（或其他语言）但界面仍然显示英文时，这通常是因为翻译文件没有被编译成二进制格式。Cura使用gettext系统进行国际化，需要将`.po`文件编译成`.mo`文件才能正常工作。

## 解决方案

本目录包含两个脚本来解决翻译文件编译问题：

### 1. Python脚本（推荐）
```bash
cd Cura
python3 compile_translations.py
```

### 2. Shell脚本（备选）
```bash
cd Cura
./compile_translations.sh
```

## 脚本功能

这些脚本会：

1. **清理现有的.mo文件** - 删除所有旧的编译文件
2. **编译Cura翻译** - 处理`Cura/resources/i18n/`目录下的所有`.po`文件
3. **编译Uranium翻译** - 处理`Uranium/resources/i18n/`目录下的所有`.po`文件
4. **创建正确的目录结构** - 在每个语言目录下创建`LC_MESSAGES`子目录
5. **生成.mo文件** - 使用`msgfmt`工具编译所有翻译文件

## 系统要求

- **msgfmt工具** (gettext包的一部分)
  - macOS: `brew install gettext`
  - Ubuntu/Debian: `sudo apt-get install gettext`
  - Windows: 从 https://mlocati.github.io/articles/gettext-iconv-windows.html 安装

## 使用步骤

1. 确保已安装gettext工具
2. 在Cura根目录下运行编译脚本
3. 重启Cura应用程序
4. 在Preferences > General > Language中选择简体中文
5. 界面应该显示为中文

## 支持的语言

脚本会编译所有可用的语言翻译，包括：

- 简体中文 (zh_CN)
- 繁体中文 (zh_TW)
- 德语 (de_DE)
- 法语 (fr_FR)
- 西班牙语 (es_ES)
- 意大利语 (it_IT)
- 日语 (ja_JP)
- 韩语 (ko_KR)
- 荷兰语 (nl_NL)
- 波兰语 (pl_PL)
- 葡萄牙语 (pt_PT, pt_BR)
- 俄语 (ru_RU)
- 芬兰语 (fi_FI)
- 匈牙利语 (hu_HU)
- 捷克语 (cs_CZ)
- 土耳其语 (tr_TR)

## 故障排除

### 如果翻译仍然不工作：

1. **检查.mo文件是否存在**：
   ```bash
   ls -la Cura/resources/i18n/zh_CN/LC_MESSAGES/
   ls -la Uranium/resources/i18n/zh_CN/LC_MESSAGES/
   ```

2. **确认Cura完全重启**：
   - 完全关闭Cura应用程序
   - 重新启动Cura

3. **检查语言设置**：
   - 在Preferences > General中确认Language设置为"简体中文"

4. **重新运行编译脚本**：
   ```bash
   cd Cura
   python3 compile_translations.py
   ```

### 常见错误：

- **"msgfmt not found"**: 需要安装gettext工具
- **权限错误**: 确保对Cura和Uranium目录有写权限
- **路径错误**: 确保在Cura根目录下运行脚本

## 文件说明

- `compile_translations.py` - Python版本的编译脚本（推荐）
- `compile_translations.sh` - Shell版本的编译脚本（备选）
- `README_TRANSLATIONS.md` - 本说明文件

## 注意事项

- 每次更新翻译文件后都需要重新运行编译脚本
- 编译过程会自动处理Cura和Uranium两个项目的翻译
- 脚本会自动创建必要的目录结构
- 编译后的.mo文件不应该提交到版本控制系统中
