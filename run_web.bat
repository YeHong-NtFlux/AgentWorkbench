@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Local Agent Workbench - Web Console

REM ================= Configuration =================
set "WB_MODELS=W:\AgentWorkbench\models"
set "D_MODELS=D:\Ollama\Models"
set "OLLAMA_EXE=C:\Users\YH_NtFlux\AppData\Local\Programs\Ollama\ollama.exe"
set "OLLAMA_APP=C:\Users\YH_NtFlux\AppData\Local\Programs\Ollama\ollama app.exe"
set "WORKBENCH_DIR=W:\AgentWorkbench"

REM ==== Option: launch the tray (ollama app.exe) after restore? 0=no (default), 1=yes ====
REM Default OFF. Restore uses a manual `serve` (proven reliable); manual serve
REM already holds 11434 so the tray would only add an icon, not a 2nd listener.
REM Turn ON only if you want the system-tray icon back after restore.
set "START_TRAY=0"

REM ================= Self-elevate to Admin (needed to kill ollama procs) =================
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo ============================================================
echo   Local Agent Workbench - Web Console
echo ============================================================
echo.

echo [1/5] Killing Ollama tray app + server (tray first, then server)...
call :kill_all
call :wait_port_free 15
if errorlevel 1 (
    echo   [FATAL] Port 11434 still occupied after kill. Aborting.
    goto :restore_and_exit
)

echo [2/5] Switching Ollama to encrypted drive (W:)...
set "OLLAMA_MODELS=%WB_MODELS%"

echo [3/5] Restarting Ollama service on W: and verifying...
start "" "%OLLAMA_EXE%" serve
call :wait_w_ready 30
if errorlevel 1 (
    echo   [FATAL] W: server did not become ready with W: content. Aborting.
    goto :restore_and_exit
)
echo   [OK] W: drive ready. Current models:
call :show_models

cd /d "%WORKBENCH_DIR%"
call .venv\Scripts\activate.bat
echo.
echo [4/5] Starting Web Console...
echo.
echo   URL: http://127.0.0.1:8765
echo   To stop: press Ctrl+C in this window, then answer N to keep restoring
echo.
python -m src.server

:restore_and_exit
echo.
echo [5/5] Workbench stopped. Restoring Ollama to D drive...
call :restore_d
echo.
echo ============================================================
echo   Restored to: D:\Ollama\Models
echo   Verification:
call :show_models
echo ============================================================
echo.
echo Done. Press any key to close.
pause >nul
exit /b 0


REM ============================================================
REM                        Subroutines
REM ============================================================
:kill_all
powershell -NoProfile -Command "Get-Process | Where-Object { $_.ProcessName -like '*ollama*' } | ForEach-Object { Stop-Process -Id $_.Id -Force }" >nul 2>&1
exit /b 0

:wait_port_free
setlocal
set /a "_max=%~1"
for /L %%i in (1,1,%_max%) do (
    powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >nul 2>&1
    if not errorlevel 1 (
        echo   ...port 11434 released after %%is
        endlocal & exit /b 0
    )
    echo   ...waiting for port release %%is ^(!_max! max^)
    timeout /t 1 >nul
)
endlocal & exit /b 1

:wait_w_ready
setlocal
set /a "_max=%~1"
for /L %%i in (1,1,%_max%) do (
    powershell -NoProfile -Command "try { $r = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2; if (($r.models.name -match 'qwen2.5') -and -not ($r.models.name -match 'qwen3-coder')) { exit 0 } } catch {}; exit 1" >nul 2>&1
    if not errorlevel 1 (
        echo   ...W: verified via API after %%is
        endlocal & exit /b 0
    )
    echo   ...waiting %%is ^(!_max! max^)
    timeout /t 1 >nul
)
endlocal & exit /b 1

:show_models
powershell -NoProfile -Command "try { (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2).models | Select-Object -ExpandProperty name } catch {}" 2>nul
exit /b 0

:restore_d
call :kill_all
call :wait_port_free 15 >nul
set "OLLAMA_MODELS=%D_MODELS%"
rem Manual serve with D: env -- proven reliable. Do NOT rely on tray to spawn
rem serve (slow/undependable -> false "restore failed"). Default: do NOT also
rem start the tray here (two listeners race on 11434). Only launch the tray when
rem START_TRAY=1 AND after manual serve already holds 11434 (tray then only adds
rem an icon, it will not spawn a 2nd listener).
start "" "%OLLAMA_EXE%" serve
powershell -NoProfile -Command "try { for ($i=0;$i -lt 60;$i++) { Start-Sleep 1; $r = Invoke-RestMethod 'http://127.0.1:11434/api/tags' -TimeoutSec 2; if ($r.models.name -match 'qwen3-coder') { exit 0 } } } catch {}" 2>nul
if "%START_TRAY%"=="1" (
    echo   [opt] START_TRAY=1 - launching tray icon...
    start "" "%OLLAMA_APP%"
)
exit /b 0
