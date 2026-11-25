"""一键启动：python run.py"""

import uvicorn

from app.config import HOST, PORT

if __name__ == "__main__":
    print("\n  AI 询盘助手已启动")
    print(f"  打开浏览器访问 → http://{HOST}:{PORT}\n")
    print("  未配置 LLM_API_KEY 时，将自动使用内置规则解析，功能完整可体验。\n")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
