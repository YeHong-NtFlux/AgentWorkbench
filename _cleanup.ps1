# ==========================================================
# AgentWorkbench 项目清理脚本
# 用途: 验收后清理临时文件、缓存、测试残留
# ==========================================================

$root = "W:\AgentWorkbench"
$removed = 0
$skipped = 0

Write-Host "=== AgentWorkbench Cleanup ===" -ForegroundColor Cyan
Write-Host "Root: $root"
Write-Host ""

# --- 1. 临时修复脚本 ---
Write-Host "[1/6] 临时脚本..." -ForegroundColor Yellow
$files = @(
    "_fix.py", "_fix2.py", "_patch.py", "_patch_v2.py",
    "_fix.py.bak", "_fix2.py.bak"
)
foreach ($f in $files) {
    $p = Join-Path $root $f
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Host "  deleted: $f" -ForegroundColor Green
        $removed++
    } else {
        $skipped++
    }
}

# --- 2. Python 编译缓存 ---
Write-Host "[2/6] __pycache__..." -ForegroundColor Yellow
$caches = Get-ChildItem $root -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
foreach ($d in $caches) {
    Remove-Item $d.FullName -Recurse -Force
    Write-Host "  deleted: $($d.FullName.Replace($root+'\',''))" -ForegroundColor Green
    $removed++
}

# --- 3. sandbox 测试残留 ---
Write-Host "[3/6] sandbox 残留..." -ForegroundColor Yellow
$sandboxJunk = @("smoke.txt", "print_numbers.py", "test.txt")
foreach ($f in $sandboxJunk) {
    $p = Join-Path $root "sandbox\$f"
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Host "  deleted: sandbox\$f" -ForegroundColor Green
        $removed++
    } else {
        $skipped++
    }
}

# --- 4. 旧版备份目录确认 ---
Write-Host "[4/6] 旧版备份..." -ForegroundColor Yellow
if (Test-Path "W:\_restore_test") {
    Remove-Item "W:\_restore_test" -Recurse -Force
    Write-Host "  deleted: W:\_restore_test" -ForegroundColor Green
    $removed++
} else {
    Write-Host "  clean (already removed)" -ForegroundColor Gray
}

# --- 5. .env 安全检查 ---
Write-Host "[5/6] .env 安全..." -ForegroundColor Yellow
$envPath = Join-Path $root ".env"
if (Test-Path $envPath) {
    $content = Get-Content $envPath -Raw
    if ($content -match "sk-[a-zA-Z0-9]{10,}") {
        Write-Host "  WARNING: .env 含有效 API key，确认 .gitignore 已覆盖" -ForegroundColor Red
    } else {
        Write-Host "  OK (no valid key detected)" -ForegroundColor Green
    }
}

# --- 6. .gitignore 确认 ---
Write-Host "[6/6] .gitignore..." -ForegroundColor Yellow
$gitignore = Join-Path $root ".gitignore"
$required = @(".env", ".venv", "__pycache__", "*.db", "sandbox/")
if (Test-Path $gitignore) {
    $gi = Get-Content $gitignore -Raw
    $missing = @()
    foreach ($r in $required) {
        if ($gi -notmatch [regex]::Escape($r)) {
            $missing += $r
        }
    }
    if ($missing.Count -eq 0) {
        Write-Host "  OK (all critical patterns covered)" -ForegroundColor Green
    } else {
        Write-Host "  MISSING in .gitignore: $($missing -join ', ')" -ForegroundColor Red
        Write-Host "  建议添加上述条目" -ForegroundColor Yellow
    }
}

# --- 汇总 ---
Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "Removed: $removed | Already clean: $skipped"

# --- 最终目录大小 ---
$size = (Get-ChildItem $root -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "Project size: $([math]::Round($size/1MB, 1)) MB (excluding .venv)"
