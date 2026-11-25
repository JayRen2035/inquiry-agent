"""FastAPI 入口：提供页面与 JSON API。"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import HOST, PORT, SAMPLES_DIR, STATIC_DIR, llm_enabled
from .db import (
    get_inquiry,
    init_db,
    insert_inquiry,
    list_inquiries,
    stats,
    update_draft,
)
from .drafter import draft_reply
from .extractor import extract
from .models import InquiryIn

app = FastAPI(title="AI 询盘助手", version="1.0.0")

SAMPLE_TITLES = {
    "email_en_inquiry": "英文询价邮件",
    "wechat_cn_inquiry": "微信群询价",
    "rfq_cn_short": "中文采购需求",
}

# 导入即建库建表，避免依赖启动事件（测试与生产都稳）
init_db()


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), media_type="text/html")


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm_enabled(), "host": HOST, "port": PORT}


@app.get("/api/samples")
def samples():
    items = []
    if os.path.isdir(SAMPLES_DIR):
        for name in sorted(os.listdir(SAMPLES_DIR)):
            if not name.endswith(".txt"):
                continue
            stem = name[:-4]
            try:
                with open(os.path.join(SAMPLES_DIR, name), "r", encoding="utf-8") as f:
                    text = f.read().strip()
            except Exception:
                continue
            if stem.startswith("wechat"):
                source = "wechat"
            elif stem.startswith("rfq") or stem.startswith("pdf"):
                source = "pdf"
            else:
                source = "email"
            items.append(
                {
                    "name": SAMPLE_TITLES.get(stem, stem),
                    "source": source,
                    "text": text,
                }
            )
    return items


@app.get("/api/inquiries")
def api_list():
    return list_inquiries()


@app.get("/api/inquiries/{item_id}")
def api_detail(item_id: int):
    item = get_inquiry(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="询盘不存在")
    return item


@app.post("/api/inquiries")
def api_create(payload: InquiryIn):
    try:
        data = extract(payload.text, payload.source)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    new_id = insert_inquiry(data)
    item = get_inquiry(new_id)
    item["engine"] = data.get("engine")
    return item


@app.post("/api/inquiries/{item_id}/draft")
def api_draft(item_id: int):
    item = get_inquiry(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="询盘不存在")
    text = draft_reply(item)
    update_draft(item_id, text)
    refreshed = get_inquiry(item_id)
    refreshed["engine"] = "llm" if llm_enabled() else "template"
    return refreshed


@app.get("/api/stats")
def api_stats():
    return stats()


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
