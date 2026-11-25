"""一键启动：python run.py"""

import os
import socket
import threading
import webbrowser

import uvicorn

from app.config import HOST, PORT


def pick_port(start: int, limit: int = 20) -> int:
    """端口被占用时自动往后找一个空闲端口，避免第一次运行就报错。"""
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, port)) != 0:
                return port
    return start


def open_browser_later(url: str) -> None:
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()


if __name__ == "__main__":
    port = pick_port(PORT)
    url = f"http://{HOST}:{port}"

    print()
    print("  AI 询盘助手已启动")
    print(f"  打开浏览器访问 → {url}")
    print()
    print("  未配置 LLM_API_KEY 时，将自动使用内置规则解析，功能完整可体验。")
    print("  关闭这个窗口或按 Ctrl+C 即可停止服务。")
    print()

    if os.environ.get("NO_BROWSER") != "1":
        open_browser_later(url)

    uvicorn.run("app.main:app", host=HOST, port=port, reload=False)
