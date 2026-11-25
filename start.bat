@echo off
chcp 65001 >nul
title AI Inquiry Agent
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   [ERROR] Python not found. Please install Python 3.9+ first:
  echo   https://www.python.org/downloads/
  echo   Remember to check "Add Python to PATH".
  echo.
  pause
  exit /b 1
)

echo.
echo   [1/2] Installing dependencies, please wait...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo   Default index is slow, retrying with a mirror...
  python -m pip install -q -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)
if errorlevel 1 (
  echo.
  echo   [ERROR] Failed to install dependencies. Check your network and run again.
  echo.
  pause
  exit /b 1
)

echo   [2/2] Starting, the browser will open automatically...
echo.
python run.py
pause
