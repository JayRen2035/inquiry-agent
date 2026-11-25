#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "[1/2] 检查依赖..."
python3 -m pip install -q -r requirements.txt

echo "[2/2] 启动服务，浏览器会自动打开..."
python3 run.py
