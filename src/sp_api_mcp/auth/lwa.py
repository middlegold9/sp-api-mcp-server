"""LWA 令牌存储 + 刷新 + 受限数据令牌（RDT）换取。

- SP-API 用 Authorization: Bearer <LWA access> + AWS SigV4。
- 含 PII 的接口（买家信息 / 收货地址）需先用 RDT 替换 Bearer。
"""

from __future__ import annotations

import threading
from typing import Optional

import httpx


class LWATokenStore:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        oauth_endpoint: str = "https://api.amazon.com/auth/o2/token",
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.oauth_endpoint = oauth_endpoint
        self._client = client or httpx.Client(timeout=30)
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._lock = threading.Lock()

    def get_access_token(self) -> str:
        """惰性刷新 access_token（约 1h 有效期），带线程锁。"""
        with self._lock:
            if self._access_token and _now() < self._expires_at - 30:
                return self._access_token
            resp = self._client.post(
                self.oauth_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            self._access_token = body["access_token"]
            self._expires_at = _now() + int(body.get("expires_in", 3600))
            return self._access_token

    def mint_rdt(
        self,
        operation: str,
        path: str,
        method: str = "GET",
        data_elements: Optional[list[str]] = None,
    ) -> str:
        """为受限（PII）操作换取一次性 RDT，作 Bearer 再带 SigV4。"""
        access = self.get_access_token()
        body = {"operation": operation, "path": path, "method": method.upper()}
        if data_elements:
            body["dataElements"] = data_elements
        resp = self._client.post(
            "https://api.amazon.com/tokens/2021-03-01/restrictedDataToken",
            json=body,
            headers={"Authorization": f"Bearer {access}"},
        )
        resp.raise_for_status()
        return resp.json()["restrictedDataToken"]


def _now() -> float:
    import time

    return time.time()
