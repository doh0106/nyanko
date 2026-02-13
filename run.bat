@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1
set PYTHONUTF8=1

REM 0) Basic environment checks and config bootstrap
call setup_windows.bat
if errorlevel 1 exit /b 1

REM 1) Start automation
python multi_ld_clicker.py --config config.json

endlocal
