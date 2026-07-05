"""广告 API 工具（US5/FR4/FR6）。

广告 API 不走 SigV4，用独立 LWA Bearer + `Amazon-Advertising-API-Scope` 头做
账号/站点路由。报表为异步：POST -> 202 Location -> 轮询 status -> 下载 gzip。
"""

from __future__ import annotations

import time
from typing import Optional

import httpx

from ..auth.ads import AdsTokenStore
from ..client import _try_json
from ..config import Settings, get_settings
from ..gateway import require_approval
from ..models import Envelope

_DEFAULT_ADS: Optional["AdsClient"] = None


class AdsClient:
    def __init__(
        self,
        settings: Settings,
        token_store: Optional[AdsTokenStore] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.settings = settings
        self.ts = token_store or AdsTokenStore(
            settings.ads_client_id,
            settings.ads_client_secret,
            settings.ads_refresh_token,
            oauth_endpoint=settings.ads_oauth_endpoint,
        )
        self._client = client or httpx.Client(timeout=60)

    def _headers(self, profile_id: str) -> dict:
        return {
            "Authorization": f"Bearer {self.ts.get_access_token()}",
            "Amazon-Advertising-API-Scope": str(profile_id),
            "Content-Type": "application/json",
        }

    def profiles_list(self) -> Envelope:
        resp = self._client.get(
            self.settings.ads_endpoint + "/v2/profiles",
            headers={"Authorization": f"Bearer {self.ts.get_access_token()}"},
        )
        if resp.status_code >= 400:
            return Envelope.err({"status": resp.status_code, "detail": _try_json(resp)})
        return Envelope.ok_response(resp.json())

    def campaigns_list(self, profile_id: str) -> Envelope:
        resp = self._client.get(
            self.settings.ads_endpoint + "/v2/sp/campaigns", headers=self._headers(profile_id)
        )
        if resp.status_code >= 400:
            return Envelope.err({"status": resp.status_code, "detail": _try_json(resp)})
        return Envelope.ok_response(resp.json())

    def _run_report(self, path: str, profile_id: str, body: dict) -> Envelope:
        resp = self._client.post(
            self.settings.ads_endpoint + path, json=body, headers=self._headers(profile_id)
        )
        if resp.status_code != 202:
            return Envelope.err({"status": resp.status_code, "detail": _try_json(resp)})
        location = resp.headers.get("Location")
        if not location:
            return Envelope.err({"detail": "no Location from report creation"})
        for _ in range(30):
            poll = self._client.get(location, headers=self._headers(profile_id))
            if poll.status_code >= 400:
                return Envelope.err({"status": poll.status_code, "detail": _try_json(poll)})
            payload = poll.json()
            status = payload.get("status")
            if status in ("COMPLETED", "DONE"):
                download_url = payload.get("location")
                if not download_url:
                    return Envelope.err({"detail": "report done but no download url", "raw": payload})
                content = self._download(download_url)
                return Envelope.ok_response({"report": payload, "content": content})
            if status in ("FATAL", "FAILURE"):
                return Envelope.err({"detail": "report failed", "raw": payload})
            time.sleep(2)
        return Envelope.err({"detail": "report polling timeout"})

    def _download(self, url: str) -> str:
        resp = self._client.get(url)
        resp.raise_for_status()
        data = resp.content
        ctype = resp.headers.get("Content-Type", "")
        if "gzip" in ctype or data[:2] == b"\x1f\x8b":
            import gzip

            data = gzip.decompress(data)
        return data.decode("utf-8")

    @require_approval
    def campaign_update(self, profile_id: str, campaign_id: str, patch: dict) -> Envelope:
        patch = {**patch, "campaignId": campaign_id}
        resp = self._client.put(
            self.settings.ads_endpoint + f"/v2/sp/campaigns/{campaign_id}",
            json=patch,
            headers=self._headers(profile_id),
        )
        if resp.status_code >= 400:
            return Envelope.err({"status": resp.status_code, "detail": _try_json(resp)})
        return Envelope.ok_response(resp.json())

    @require_approval
    def negative_keyword_create(self, profile_id: str, body: dict) -> Envelope:
        resp = self._client.post(
            self.settings.ads_endpoint + "/v2/sp/negativeKeywords",
            json=body,
            headers=self._headers(profile_id),
        )
        if resp.status_code >= 400:
            return Envelope.err({"status": resp.status_code, "detail": _try_json(resp)})
        return Envelope.ok_response(resp.json())


def get_default_ads_client() -> AdsClient:
    global _DEFAULT_ADS
    if _DEFAULT_ADS is None:
        _DEFAULT_ADS = AdsClient(get_settings())
    return _DEFAULT_ADS


# ---- MCP 暴露的工具函数 ----
def ads_profiles_list():
    return get_default_ads_client().profiles_list()


def ads_campaigns_list(profile_id: str):
    return get_default_ads_client().campaigns_list(profile_id)


def ads_performance_report(
    profile_id: str,
    record_type: str = "campaigns",
    metrics: Optional[list] = None,
    report_date: Optional[str] = None,
):
    body = {
        "reportDate": report_date,
        "metrics": ",".join(metrics) if metrics else "campaignName,campaignId,impressions,clicks,cost,attributedConversions1d,attributedSales1d",
    }
    return get_default_ads_client()._run_report(f"/v2/sp/{record_type}/report", profile_id, body)


def ads_searchterms_report(
    profile_id: str,
    report_date: str,
    metrics: Optional[list] = None,
):
    body = {
        "reportDate": report_date,
        "metrics": ",".join(metrics) if metrics else "keywordId,keywordText,query,impressions,clicks,cost,attributedConversions1d,attributedSales1d",
    }
    return get_default_ads_client()._run_report("/v2/sp/keywords/searchterms/report", profile_id, body)


__all__ = [
    "ads_profiles_list",
    "ads_campaigns_list",
    "ads_performance_report",
    "ads_searchterms_report",
]
