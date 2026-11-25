"""回复草拟：根据抽取结果生成一封可直接改用的回复。"""

import re

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, llm_enabled

DRAFT_SYSTEM_PROMPT = """你是外贸业务员，需要根据已抽取的询盘信息，草拟一封专业、简洁的回复。
要求：
1. 语言跟随客户：客户用英文就用英文，用中文就用中文。
2. 结构：感谢询盘 → 确认已了解的需求 → 列出需要客户补充的信息 → 结尾礼貌收束。
3. 只写正文，不要主题行，不要解释，不要编造价格或交期。
4. 语气专业、不卑不亢，控制在 200 字以内。"""


def _has_chinese(s: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fa5]", s or ""))


def _draft_with_llm(record: dict) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    facts = {
        "company": record.get("company"),
        "contact": record.get("contact"),
        "country": record.get("country"),
        "product": record.get("product"),
        "quantity": record.get("quantity"),
        "target_price": record.get("target_price"),
        "delivery": record.get("delivery"),
        "incoterm": record.get("incoterm"),
        "missing_info": record.get("missing_info"),
        "raw_text": (record.get("raw_text") or "")[:1500],
    }
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
            {"role": "user", "content": str(facts)},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def _draft_with_template(record: dict) -> str:
    chinese = _has_chinese(record.get("raw_text", ""))
    product = record.get("product") or ("贵司咨询的产品" if chinese else "the product you inquired about")
    contact = record.get("contact")
    missing = record.get("missing_info") or []

    if chinese:
        greet = f"{contact} 您好：" if contact else "您好："
        lines = [
            greet,
            "",
            f"感谢您对 {product} 的询盘，我们已收到并初步了解了您的需求。",
        ]
        if record.get("quantity"):
            lines.append(f"您提到的数量为：{record['quantity']}。")
        if record.get("incoterm"):
            lines.append(f"贸易条款：{record['incoterm']}。")
        if missing:
            lines.append("")
            lines.append("为了给您准确报价，还请您补充以下信息：")
            lines += [f"{i}. {m}" for i, m in enumerate(missing, 1)]
        lines += [
            "",
            "收到补充信息后，我们会尽快提供正式报价与交期。期待与您合作。",
            "",
            "此致",
        ]
        return "\n".join(lines)

    greet = f"Dear {contact}," if contact else "Dear Sir/Madam,"
    lines = [
        greet,
        "",
        f"Thank you for your inquiry about {product}. We have received your request and noted the details.",
    ]
    if record.get("quantity"):
        lines.append(f"Quantity mentioned: {record['quantity']}.")
    if record.get("incoterm"):
        lines.append(f"Incoterms: {record['incoterm']}.")
    if missing:
        lines.append("")
        lines.append("To prepare an accurate quotation, could you please confirm the following:")
        lines += [f"{i}. {m}" for i, m in enumerate(missing, 1)]
    lines += [
        "",
        "Once we have these details, we will send you a formal quotation and lead time shortly.",
        "Looking forward to working with you.",
        "",
        "Best regards,",
    ]
    return "\n".join(lines)


def draft_reply(record: dict) -> str:
    """对外统一入口：有 Key 走大模型，否则用模板，保证永远有可用草稿。"""
    if llm_enabled():
        try:
            text = _draft_with_llm(record)
            if text:
                return text
        except Exception:
            pass
    return _draft_with_template(record)
