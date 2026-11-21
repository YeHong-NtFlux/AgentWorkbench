@echo off
setlocal EnableExtensions

set "D_MODELS=D:\Ollama\Models"
set "OLLAMA_EXE=C:\Users\YH_NtFlux\AppData\Local\Programs\Ollama\ollama.exe"

echo ============================================================
echo   Emergency Restore - Switch Ollama back to D drive
echo ============================================================
echo.

set "OLLAMA_MODELS=%D_MODELS%"
taskkill /IM ollama.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul
start "" "%OLLAMA_EXE%" serve
timeout /t 3 /nobreak >nul

echo.
echo   Restored. Current models:
echo.
ollama list
echo.
pause
