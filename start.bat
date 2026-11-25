@echo off
chcp 65001 >nul
echo.
echo   正在安装依赖（第一次会慢一点）...
python -m pip install -r requirements.txt
echo.
echo   启动 AI 询盘助手...
python run.py
pause
