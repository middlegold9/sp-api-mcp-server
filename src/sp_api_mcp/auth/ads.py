"""广告 API 令牌存储（独立 OAuth）+ profile 路由。

广告 API 与 SP-API 共享 LWA，但端点独立，且每次调用需带
`Amazon-Advertising-API-Scope: <profileId>` 头做账号/站点路由。
"""

from __future__ import annotations

import threading
from typing import Optional

import httpx


class AdsTokenStore:
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


def _now() -> float:
    import time

    return time.time()
