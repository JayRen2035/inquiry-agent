"""询盘抽取：有 Key 走大模型，没 Key 走内置规则，保证任何时候都能用。"""

import json
import re
from typing import Optional

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, llm_enabled

FIELDS = [
    "company",
    "contact",
    "country",
    "product",
    "quantity",
    "target_price",
    "delivery",
    "incoterm",
    "urgency",
    "intent",
    "summary",
    "missing_info",
    "confidence",
]

EXTRACT_SYSTEM_PROMPT = """你是外贸/销售团队的询盘信息抽取助手。
请从用户提供的询盘文本中抽取字段，并且只输出一个 JSON 对象，不要任何解释。

字段定义：
- company: 客户公司名，没有则 null
- contact: 联系人姓名，没有则 null
- country: 国家或地区，没有则 null
- product: 客户想采购的产品/型号，没有则 null
- quantity: 采购数量（保留原文单位，如 "5000 pcs"），没有则 null
- target_price: 目标价或预算，没有则 null
- delivery: 交期要求，没有则 null
- incoterm: 贸易条款（FOB/CIF/EXW 等），没有则 null
- urgency: 紧急程度，只能是 "high" / "medium" / "low"
- intent: 意图，只能是 "询价" / "样品" / "售后" / "合作" / "其他"
- summary: 一句话中文摘要，不超过 40 字
- missing_info: 缺失的关键信息列表（从 company/contact/country/product/quantity/target_price/delivery 里挑缺失的，用中文字段名）
- confidence: 抽取置信度，0 到 1 的小数

注意：不要在 JSON 里编造原文没有的信息。"""


def _normalize(data: dict) -> dict:
    """把模型或规则的结果收敛成统一结构，避免前端拿到脏数据。"""
    out = {}
    text_fields = [
        "company",
        "contact",
        "country",
        "product",
        "quantity",
        "target_price",
        "delivery",
        "incoterm",
    ]
    for f in text_fields:
        v = data.get(f)
        if v is None:
            out[f] = None
        else:
            v = str(v).strip()
            out[f] = v if v and v.lower() not in ("null", "none", "未知", "无") else None

    urgency = str(data.get("urgency") or "medium").strip().lower()
    out["urgency"] = urgency if urgency in ("high", "medium", "low") else "medium"

    intent = str(data.get("intent") or "其他").strip()
    if intent not in ("询价", "样品", "售后", "合作", "其他"):
        intent = "其他"
    out["intent"] = intent

    out["summary"] = str(data.get("summary") or "").strip()[:60]

    missing = data.get("missing_info") or []
    if isinstance(missing, str):
        missing = [m.strip() for m in re.split(r"[,，、;；]", missing) if m.strip()]
    out["missing_info"] = [str(m) for m in missing][:8]

    try:
        conf = float(data.get("confidence") or 0)
    except Exception:
        conf = 0.0
    out["confidence"] = max(0.0, min(1.0, conf))
    return out


def _extract_with_llm(text: str) -> Optional[dict]:
    if not llm_enabled():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
                {"role": "user", "content": text[:6000]},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        return _normalize(json.loads(content))
    except Exception:
        return None


COUNTRY_WORDS = {
    "usa": "美国", "united states": "美国", "america": "美国", "germany": "德国",
    "uk": "英国", "united kingdom": "英国", "france": "法国", "italy": "意大利",
    "spain": "西班牙", "netherlands": "荷兰", "poland": "波兰", "russia": "俄罗斯",
    "brazil": "巴西", "mexico": "墨西哥", "canada": "加拿大", "australia": "澳大利亚",
    "japan": "日本", "korea": "韩国", "india": "印度", "vietnam": "越南",
    "thailand": "泰国", "singapore": "新加坡", "uae": "阿联酋", "saudi": "沙特",
    "美国": "美国", "德国": "德国", "英国": "英国", "法国": "法国", "日本": "日本",
    "韩国": "韩国", "印度": "印度", "越南": "越南", "巴西": "巴西", "俄罗斯": "俄罗斯",
    "澳大利亚": "澳大利亚", "加拿大": "加拿大", "西班牙": "西班牙", "意大利": "意大利",
    "荷兰": "荷兰", "波兰": "波兰", "泰国": "泰国", "新加坡": "新加坡",
    "阿联酋": "阿联酋", "沙特": "沙特",
}

COMPANY_HINTS = ("co.,", "co.,ltd", "ltd", "limited", "inc", "gmbh", "srl", "llc", "公司", "集团")


def _clean(value: str, maxlen: int = 60) -> str:
    """去掉首尾标点、截断到第一个分句。"""
    s = str(value).strip()
    # 只按中文标点/换行截断，保留英文公司名里的逗号（如 Co., Ltd）
    s = re.split(r"[，。;；\n]", s)[0].strip()
    s = re.sub(r"^(型号是|型号|是|is|为)\s*", "", s)
    return s.strip(" .:：-—\"'")[:maxlen]


def _extract_with_rules(text: str) -> dict:
    """无大模型时的兜底规则解析：能抓多少抓多少，标低置信度。"""
    flat = re.sub(r"\s+", " ", text).strip()
    low = flat.lower()
    result = {f: None for f in FIELDS}
    result["confidence"] = 0.4

    # 公司：优先中文"…公司/集团"，其次英文"…Co., Ltd / Ltd / Inc …"
    m = re.search(r"([A-Za-z\u4e00-\u9fa5&\.\,\- ]{2,50}(?:有限公司|股份有限公司|集团|公司))", text)
    if m:
        result["company"] = _clean(m.group(1))
    else:
        m = re.search(
            r"((?:[A-Z][A-Za-z0-9&\.\-]*\s+){0,4}(?:Co\.,?\s*Ltd\.?|Ltd\.?|Limited|Inc\.?|GmbH|LLC|Srl|Corp\.?))",
            text,
        )
        if m:
            result["company"] = _clean(m.group(1))

    # 联系人：显式标注，或署名
    m = re.search(r"(?:联系人|contact person|attn)\s*[:：]?\s*([A-Za-z\u4e00-\u9fa5·]{2,20})", text, re.I)
    if m:
        result["contact"] = m.group(1).strip()
    else:
        m = re.search(
            r"(?:best regards|regards|此致|谢谢)[,，]?\s*\n+\s*([A-Za-z\u4e00-\u9fa5· ]{2,20})",
            text,
            re.I,
        )
        if m:
            result["contact"] = m.group(1).strip()

    # 国家
    for kw, cn in COUNTRY_WORDS.items():
        if kw in low:
            result["country"] = cn
            break

    # 数量
    m = re.search(r"(\d[\d,\.]*\s*(?:pcs|pieces|units|sets|个|台|件|套|箱|吨))", flat, re.I)
    if m:
        result["quantity"] = m.group(1)

    # 目标价
    m = re.search(
        r"(?:target price|目标价|预算|价格|报价)[^\n]{0,20}?"
        r"([A-Z]{3}\s?\d[\d,\.]*|\$\s?\d[\d,\.]*|￥\s?\d[\d,\.]*|€\s?\d[\d,\.]*|\d[\d,\.]*\s?元)",
        text,
        re.I,
    )
    if m:
        result["target_price"] = m.group(1).strip()

    # 交期
    m = re.search(r"(?:delivery|交期|交货期|交货时间)\s*[:：]?\s*([^\n。；;，,]{1,30})", text, re.I)
    if m:
        result["delivery"] = m.group(1).strip()

    # 贸易条款
    m = re.search(r"\b(FOB|CIF|EXW|DDP|DAP|CFR)\b", text, re.I)
    if m:
        result["incoterm"] = m.group(1).upper()

    # 产品
    for line in text.splitlines():
        m = re.search(r"(?:product|model|产品|型号)\s*(?:is|:)?\s*[:：]?\s*(.+)", line, re.I)
        if m:
            val = _clean(m.group(1))
            if val:
                result["product"] = val
                break

    # 意图（顺序即优先级）
    if re.search(r"售后|维修|保修|退货|repair|after[- ]?sales|return", low):
        result["intent"] = "售后"
    elif re.search(r"sample|样品|打样", low):
        result["intent"] = "样品"
    elif re.search(r"cooperat|agent|distributor|合作|代理|经销", low):
        result["intent"] = "合作"
    elif re.search(r"price|quote|quotation|报价|询价|采购|purchase|rfq", low):
        result["intent"] = "询价"
    else:
        result["intent"] = "其他"

    # 紧急度
    if re.search(r"urgent|asap|尽快|急|马上|immediately", low):
        result["urgency"] = "high"
    elif re.search(r"no rush|不急|以后|future", low):
        result["urgency"] = "low"
    else:
        result["urgency"] = "medium"

    # 摘要：第一行
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    result["summary"] = first[:40]

    # 缺失信息
    label = {
        "company": "公司", "contact": "联系人", "country": "国家", "product": "产品",
        "quantity": "数量", "target_price": "目标价", "delivery": "交期",
    }
    result["missing_info"] = [label[k] for k in label if not result.get(k)]

    return _normalize(result)


def extract(text: str, source: str = "email") -> dict:
    """对外统一入口：优先大模型，失败则规则兜底。"""
    if not text or not text.strip():
        raise ValueError("询盘内容为空")

    data = _extract_with_llm(text)
    engine = "llm"
    if data is None:
        data = _extract_with_rules(text)
        engine = "rules"

    return {
        "raw_text": text.strip(),
        "source": source,
        **data,
        "engine": engine,
        "status": "new",
        "draft": None,
    }
