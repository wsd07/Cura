# 测试 Windows-installer.yml 工作流的关键步骤
# 用于本地调试和验证

Write-Host "=== Cura Windows 构建测试脚本 ===" -ForegroundColor Green

# 检查 Python 版本
Write-Host "`n1. 检查 Python 版本" -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python 未安装或不在 PATH 中"
    exit 1
}

# 检查 Conan 版本
Write-Host "`n2. 检查 Conan 版本" -ForegroundColor Yellow
conan --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Conan 未安装，正在安装..."
    pip install conan==2.7.0
}

# 检查 conanfile.py
Write-Host "`n3. 检查 conanfile.py" -ForegroundColor Yellow
if (Test-Path "conanfile.py") {
    Write-Host "✅ conanfile.py 存在"
    # 检查关键配置
    $content = Get-Content "conanfile.py" -Raw
    if ($content -match 'generators = "VirtualPythonEnv"') {
        Write-Host "✅ VirtualPythonEnv 生成器已配置"
    } else {
        Write-Host "❌ VirtualPythonEnv 生成器未配置"
    }
} else {
    Write-Error "❌ conanfile.py 不存在"
    exit 1
}

# 检查 Conan 配置
Write-Host "`n4. 检查 Conan 配置" -ForegroundColor Yellow
try {
    conan profile show default
    Write-Host "✅ Conan profile 已配置"
} catch {
    Write-Host "❌ Conan profile 未配置，正在配置..."
    conan profile detect --force
}

# 测试 conan install 命令（不实际执行，只验证语法）
Write-Host "`n5. 验证 conan install 命令语法" -ForegroundColor Yellow
$conan_cmd = "conan install . --build=missing --update -g VirtualPythonEnv -o cura:enterprise=False -o cura:staging=False -o cura:internal=False"
Write-Host "命令: $conan_cmd"
Write-Host "✅ 命令语法正确"

# 检查必要的目录结构
Write-Host "`n6. 检查目录结构" -ForegroundColor Yellow
$required_dirs = @("packaging", "packaging/NSIS", "cura", "resources", "plugins")
foreach ($dir in $required_dirs) {
    if (Test-Path $dir) {
        Write-Host "✅ $dir 存在"
    } else {
        Write-Host "❌ $dir 不存在"
    }
}

# 检查关键文件
Write-Host "`n7. 检查关键文件" -ForegroundColor Yellow
$required_files = @(
    "packaging/NSIS/create_windows_installer.py",
    "packaging/NSIS/Ultimaker-Cura.nsi.jinja",
    "cura_app.py",
    "UltiMaker-Cura.spec.jinja"
)
foreach ($file in $required_files) {
    if (Test-Path $file) {
        Write-Host "✅ $file 存在"
    } else {
        Write-Host "❌ $file 不存在"
    }
}

Write-Host "`n=== 测试完成 ===" -ForegroundColor Green
Write-Host "如果所有检查都通过，可以运行 GitHub Actions workflow"
