"""SP-API 客户端：SigV4 签名 + 限流退避 + 缓存 + 出参信封。"""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx

from ..auth.lwa import LWATokenStore
from ..config import Settings, get_settings
from ..models import Envelope

# 指数退避档位（秒）
_BACKOFF = [1, 2, 4, 8, 16]


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sign(req: httpx.Request, settings: Settings) -> None:
    """用 botocore 计算 AWS SigV4 签名并写回请求头。"""
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    from botocore.credentials import Credentials

    creds = Credentials(settings.aws_access_key_id, settings.aws_secret_access_key)
    aws_req = AWSRequest(
        method=req.method,
        url=str(req.url),
        data=req.content,
        headers=dict(req.headers),
    )
    SigV4Auth(creds, "execute-api", settings.sp_api_region).add_auth(aws_req)
    for key, val in aws_req.headers.items():
        req.headers[key] = val


class SPAPIClient:
    def __init__(
        self,
        settings: Settings,
        lwa: Optional[LWATokenStore] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.settings = settings
        self.lwa = lwa or LWATokenStore(
            settings.lwa_client_id,
            settings.lwa_client_secret,
            settings.lwa_refresh_token,
        )
        self._client = client or httpx.Client(timeout=60)
        self._cache: dict[str, Any] = {}
        self._cache_exp: dict[str, float] = {}

    # ---- 读接口（带缓存 + 退避） ----
    def call(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        *,
        use_rdt: bool = False,
        data_elements: Optional[list[str]] = None,
        operation: Optional[str] = None,
        cache_ttl: Optional[int] = None,
        skip_cache: bool = False,
    ) -> Envelope:
        url = self.settings.sp_api_endpoint + path
        method = method.upper()
        cache_key: Optional[str] = None
        if method == "GET" and not skip_cache:
            cache_key = f"{path}|{_dumps(params)}|{_dumps(json_body)}"
            if cache_key in self._cache and time.time() < self._cache_exp[cache_key]:
                return Envelope.ok_response(self._cache[cache_key], cached=True)

        access = self.lwa.get_access_token()
        token = access
        if use_rdt:
            token = self.lwa.mint_rdt(
                operation=operation or path,
                path=path,
                method=method,
                data_elements=data_elements,
            )
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-amz-access-token": token,
        }

        last_status = None
        last_body: Any = None
        for attempt in range(len(_BACKOFF) + 1):
            req = self._client.build_request(
                method, url, params=params, json=json_body, headers=headers
            )
            _sign(req, self.settings)
            resp = self._client.send(req)
            rate_remaining = _to_int(resp.headers.get("x-amzn-RateLimit-Limit"))
            if resp.status_code in (429,) or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else _BACKOFF[min(attempt, len(_BACKOFF) - 1)]
                time.sleep(wait)
                last_status, last_body = resp.status_code, _try_json(resp)
                continue
            if resp.status_code >= 400:
                return Envelope.err(
                    {"status": resp.status_code, "detail": _try_json(resp)},
                    rate_remaining=rate_remaining,
                )
            data = _try_json(resp)
            if cache_key:
                self._cache[cache_key] = data
                self._cache_exp[cache_key] = time.time() + (cache_ttl or self.settings.cache_ttl)
            return Envelope.ok_response(data, rate_remaining=rate_remaining)
        return Envelope.err(
            {"status": last_status or 0, "detail": last_body or "max retries exceeded"},
        )

    # ---- 报表文档下载（SP-API 报表常为裸 gzip） ----
    def download_document(self, url: str) -> str:
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.content
        ctype = resp.headers.get("Content-Type", "")
        if "gzip" in ctype or data[:2] == b"\x1f\x8b":
            import gzip

            data = gzip.decompress(data)
        return data.decode("utf-8")


def _dumps(obj: Optional[dict]) -> str:
    import json

    return json.dumps(obj or {}, sort_keys=True)


def _try_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


# ---- 默认客户端注册表（供 tools 使用，测试可替换） ----
_DEFAULT: Optional[SPAPIClient] = None


def set_default_client(client: SPAPIClient) -> None:
    global _DEFAULT
    _DEFAULT = client


def get_default_client() -> SPAPIClient:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = SPAPIClient(get_settings())
    return _DEFAULT
