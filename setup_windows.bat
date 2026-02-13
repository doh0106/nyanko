@echo off
setlocal enabledelayedexpansion

echo [1/5] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  echo         Install Python 3 and enable "Add python.exe to PATH".
  exit /b 1
)
python --version

echo [2/5] Checking ADB...
where adb >nul 2>nul
if errorlevel 1 (
  echo [ERROR] adb not found in PATH.
  echo         Install Android platform-tools and add to PATH.
  echo         (Optional) winget install --id Google.AndroidSDK.PlatformTools -e
  exit /b 1
)
adb version

echo [3/5] Checking connected emulator devices...
adb devices

echo [4/5] Preparing config.json...
if not exist config.json (
  copy /Y config.example.json config.json >nul
  echo [INFO] Created config.json from config.example.json
) else (
  echo [INFO] config.json already exists
)

echo [5/5] Done. You can now run: run.bat
endlocal
