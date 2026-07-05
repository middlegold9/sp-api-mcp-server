import gzip

import httpx
import respx

from sp_api_mcp.tools import advertising as adv

TOKEN = "https://api.amazon.com/auth/o2/token"
ADS = "https://advertising-api.amazon.com"


@respx.mock
def test_profiles_list():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    respx.get(ADS + "/v2/profiles").mock(
        return_value=httpx.Response(200, json=[{"profileId": 123, "countryCode": "US"}])
    )
    env = adv.ads_profiles_list()
    assert env.ok is True
    assert env.data[0]["profileId"] == 123


@respx.mock
def test_performance_report_async_flow():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    respx.post(ADS + "/v2/sp/campaigns/report").mock(
        return_value=httpx.Response(202, headers={"Location": ADS + "/v2/sp/campaigns/report/abc"})
    )
    respx.get(ADS + "/v2/sp/campaigns/report/abc").mock(
        return_value=httpx.Response(200, json={"status": "COMPLETED", "location": ADS + "/dl/abc"})
    )
    content = gzip.compress(b"campaignId,impressions\n123,10")
    respx.get(ADS + "/dl/abc").mock(
        return_value=httpx.Response(200, content=content, headers={"Content-Type": "application/gzip"})
    )
    env = adv.ads_performance_report("123", record_type="campaigns", report_date="2024-01-01")
    assert env.ok is True
    assert "campaignId" in env.data["content"]


@respx.mock
def test_searchterms_report_async_flow():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    respx.post(ADS + "/v2/sp/keywords/searchterms/report").mock(
        return_value=httpx.Response(202, headers={"Location": ADS + "/v2/sp/keywords/searchterms/report/xyz"})
    )
    respx.get(ADS + "/v2/sp/keywords/searchterms/report/xyz").mock(
        return_value=httpx.Response(200, json={"status": "DONE", "location": ADS + "/dl/xyz"})
    )
    content = gzip.compress(b"query,clicks\nred shoes,3")
    respx.get(ADS + "/dl/xyz").mock(
        return_value=httpx.Response(200, content=content, headers={"Content-Type": "application/gzip"})
    )
    env = adv.ads_searchterms_report("123", report_date="2024-01-01")
    assert env.ok is True
    assert "red shoes" in env.data["content"]
