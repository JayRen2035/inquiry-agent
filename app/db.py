"""SQLite 存储层：自动建库建表，调用方无需关心。"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT,
                raw_text TEXT,
                company TEXT,
                contact TEXT,
                country TEXT,
                product TEXT,
                quantity TEXT,
                target_price TEXT,
                delivery TEXT,
                incoterm TEXT,
                urgency TEXT,
                intent TEXT,
                summary TEXT,
                missing_info TEXT,
                confidence REAL,
                status TEXT,
                draft TEXT
            )
            """
        )


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["missing_info"] = json.loads(d.get("missing_info") or "[]")
    return d


def insert_inquiry(d: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO inquiries
            (created_at, source, raw_text, company, contact, country, product,
             quantity, target_price, delivery, incoterm, urgency, intent, summary,
             missing_info, confidence, status, draft)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                now,
                d.get("source"),
                d.get("raw_text"),
                d.get("company"),
                d.get("contact"),
                d.get("country"),
                d.get("product"),
                d.get("quantity"),
                d.get("target_price"),
                d.get("delivery"),
                d.get("incoterm"),
                d.get("urgency"),
                d.get("intent"),
                d.get("summary"),
                json.dumps(d.get("missing_info", []), ensure_ascii=False),
                float(d.get("confidence", 0) or 0),
                d.get("status", "new"),
                d.get("draft"),
            ),
        )
        return int(cur.lastrowid)


def list_inquiries():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM inquiries ORDER BY id DESC").fetchall()
    return [_row_to_dict(r) for r in rows]


def get_inquiry(item_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (item_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_draft(item_id: int, draft: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE inquiries SET draft = ?, status = 'drafted' WHERE id = ?",
            (draft, item_id),
        )


def stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM inquiries").fetchone()["c"]
        drafted = conn.execute(
            "SELECT COUNT(*) AS c FROM inquiries WHERE status = 'drafted'"
        ).fetchone()["c"]
        high = conn.execute(
            "SELECT COUNT(*) AS c FROM inquiries WHERE urgency = 'high'"
        ).fetchone()["c"]
    return {"total": total, "drafted": drafted, "high_priority": high}
