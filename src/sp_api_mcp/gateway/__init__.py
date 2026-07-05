"""写操作审批网关：默认关闭，需显式开启（FR6 人类在环）。"""

from __future__ import annotations

import functools

from ..config import get_settings
from ..models import Envelope


def writes_allowed() -> bool:
    return bool(get_settings().approve_writes)


def require_approval(func):
    """装饰写工具：未开启审批时返回 blocked 信封，不执行真实写。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if not writes_allowed():
            return Envelope.err(
                {
                    "blocked": True,
                    "reason": "approval required: set APPROVE_WRITES=true to enable write tools",
                    "tool": func.__name__,
                }
            )
        return func(*args, **kwargs)

    return wrapper
