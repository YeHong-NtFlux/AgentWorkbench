@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Restore Ollama to D drive (daily state)

set "OLLAMA_EXE=C:\Users\YH_NtFlux\AppData\Local\Programs\Ollama\ollama.exe"
set "OLLAMA_APP=C:\Users\YH_NtFlux\AppData\Local\Programs\Ollama\ollama app.exe"
set "D_MODELS=D:\Ollama\Models"

REM ==== Option: launch the tray (ollama app.exe) after restore? 0=no (default), 1=yes ====
REM Default OFF: restore uses a manual `serve` (proven reliable). The tray is a
REM menu-only helper; since manual serve already holds 11434, the tray will just
REM show its icon and won't spawn a 2nd listener -- safe, but unnecessary. Turn ON
REM only if you want the system-tray icon back after restore.
set "START_TRAY=0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   Restore Ollama to D drive (daily state)
echo ============================================================
echo.

echo [1/3] Killing tray app + server...
powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -like '*ollama*' } | ForEach-Object { Stop-Process -Id $_.Id -Force }" >nul 2>&1

echo [2/3] Waiting for port release, then starting server on D: ...
for /L %%i in (1,1,15) do (
    powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>&1
    if not errorlevel 1 goto :portfree
    timeout /t 1 >nul
)
:portfree
rem Launch a MANUAL server with OLLAMA_MODELS=D: -- this is the method proven
rem reliable across all tests (serves D: content, single listener, obeys env).
rem Do NOT rely on the tray `ollama app` to spawn serve -- it is slow/undependable
rem and caused the false "restore failed". Do NOT also start the tray here,
rem otherwise two listeners race on 11434.
set "OLLAMA_MODELS=%D_MODELS%"
start "" "%OLLAMA_EXE%" serve

echo [3/3] Polling ready (expect qwen3-coder, up to 60s)...
powershell -NoProfile -Command "try { for ($i=0;$i -lt 60;$i++) { Start-Sleep 1; $r = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; if ($r.models.name -match 'qwen3-coder') { Write-Host ''; Write-Host ('  [OK] Restored to D:\Ollama\Models. Models after ' + ($i+1) + 's:'); $r.models | Select-Object -ExpandProperty name; exit 0 } } } catch {}; Write-Warning 'restore failed - run restore_ollama.bat again'" 2>nul

REM ==== Optionally bring back the tray icon (manual serve already holds 11434,
REM so the tray only shows the icon and will NOT spawn a 2nd listener) ====
if "%START_TRAY%"=="1" (
    echo   [opt] START_TRAY=1 - launching tray icon...
    start "" "%OLLAMA_APP%"
)

echo.
echo Done. Press any key to close.
pause >nul
exit /b 0
