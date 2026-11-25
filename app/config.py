"""全局配置：全部来自环境变量，未配置也能跑。"""

import os

# 读取 .env（如果装了 python-dotenv）
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 服务
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# 数据库（SQLite，首次启动自动创建，无需安装）
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "inquiries.db"))

# 大模型（可选）。OpenAI 兼容接口均可：OpenAI / DeepSeek / 通义 / Kimi 等
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")


def llm_enabled() -> bool:
    """有 Key 且装了 openai 才启用大模型，否则自动走规则解析。"""
    if not LLM_API_KEY:
        return False
    try:
        import openai  # noqa: F401

        return True
    except Exception:
        return False
