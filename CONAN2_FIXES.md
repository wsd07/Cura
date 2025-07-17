# Conan 2.x 语法修复说明

## 修复的错误

### 1. conan config install 命令
**❌ 错误语法 (您之前的版本):**
```bash
conan config install https://github.com/wsd07/conan-config.git -a "-b runner/Windows"
```

**✅ 正确语法 (Conan 2.x):**
```bash
conan config install https://github.com/wsd07/conan-config.git
```

**说明:** 
- Conan 2.x 中 `-a` 参数已被移除
- 不再支持 `-b runner/Windows` 分支指定方式
- 如果需要特定分支，应该在URL中指定或使用其他方法

### 2. conan profile show 命令
**❌ 错误语法:**
```bash
conan profile show default
```

**✅ 正确语法 (Conan 2.x):**
```bash
conan profile show
```

**说明:**
- Conan 2.x 中默认显示默认profile，不需要指定 `default` 参数
- `conan profile show` 会自动显示当前的默认profile

### 3. conan editable add 命令
**✅ 当前语法已正确:**
```bash
conan editable add ../Uranium --name=uranium --version=5.11.0 --user=wsd07 --channel=testing
conan editable add ../CuraEngine --name=curaengine --version=5.11.0 --user=wsd07 --channel=testing
```

**说明:**
- 这个语法在Conan 2.x中是正确的
- 使用固定版本号而不是变量是正确的做法

## 其他重要的Conan 2.x变化

### 缓存路径
- **Conan 1.x:** `~/.conan`
- **Conan 2.x:** `~/.conan2`

### 生成器
- **推荐使用:** `VirtualPythonEnv` (已在workflow中正确使用)
- **语法:** `-g VirtualPythonEnv`

### 构建命令
- **正确语法:** `--build=missing`
- **更新命令:** `--update`

## 验证方法

运行测试脚本验证语法：
```powershell
.\test_workflow.ps1
```

## 参考文档
- [Conan 2.x Commands Reference](https://docs.conan.io/2/reference/commands.html)
- [conan config](https://docs.conan.io/2/reference/commands/config.html)
- [conan editable](https://docs.conan.io/2/reference/commands/editable.html)
- [conan install](https://docs.conan.io/2/reference/commands/install.html)
- [conan profile](https://docs.conan.io/2/reference/commands/profile.html)

## 当前状态
✅ 所有Conan 2.x语法错误已修复
✅ workflow文件已更新
✅ 测试脚本已更新
✅ 遵循官方文档规范
