"""数据模型：出参信封、凭证、调用记录、报表任务。"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Envelope(BaseModel):
    """所有 MCP 工具的统一出参信封（FR：可验证 / 可复盘）。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    data: Any = None
    request_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    rate_remaining: Optional[int] = None
    cached: bool = False
    error: Optional[Any] = None

    @classmethod
    def ok_response(
        cls, data: Any, rate_remaining: Optional[int] = None, cached: bool = False
    ) -> "Envelope":
        return cls(ok=True, data=data, rate_remaining=rate_remaining, cached=cached)

    @classmethod
    def err(cls, error: Any, rate_remaining: Optional[int] = None) -> "Envelope":
        return cls(ok=False, error=error, rate_remaining=rate_remaining)


class SellerCredential(BaseModel):
    """卖家凭证（敏感字段在持久化层应加密，这里仅作内存模型）。"""

    seller_id: str
    marketplace_ids: list[str]
    region: str = "us-east-1"
    lwa_refresh_token: str
    ads_refresh_token: Optional[str] = None


class ToolCall(BaseModel):
    """一次工具调用的可观测记录（用于复盘）。"""

    tool: str
    args: dict
    ts: float
    latency_ms: int
    status: str
    cached: bool = False


class ReportJob(BaseModel):
    """异步报表任务状态。"""

    report_type: str
    status: str
    report_id: Optional[str] = None
    document_url: Optional[str] = None
    expires: Optional[str] = None
