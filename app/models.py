"""请求 / 响应用的数据模型。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class InquiryIn(BaseModel):
    text: str = Field(..., description="原始询盘文本")
    source: str = Field("email", description="来源：email / wechat / pdf / other")


class ExtractedFields(BaseModel):
    company: Optional[str] = None
    contact: Optional[str] = None
    country: Optional[str] = None
    product: Optional[str] = None
    quantity: Optional[str] = None
    target_price: Optional[str] = None
    delivery: Optional[str] = None
    incoterm: Optional[str] = None
    urgency: str = "medium"
    intent: str = "其他"
    summary: str = ""
    missing_info: List[str] = []
    confidence: float = 0.0
