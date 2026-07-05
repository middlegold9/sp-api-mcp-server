import httpx
import respx

from sp_api_mcp.auth.lwa import LWATokenStore

TOKEN = "https://api.amazon.com/auth/o2/token"


@respx.mock
def test_access_token_refresh_and_cache():
    route = respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at1", "expires_in": 3600})
    )
    store = LWATokenStore("c", "s", "r")
    t1 = store.get_access_token()
    t2 = store.get_access_token()
    assert t1 == t2 == "at1"
    # 缓存命中，不应再次刷新
    assert route.call_count == 1


@respx.mock
def test_access_token_refreshes_after_expiry():
    route = respx.post(TOKEN)
    route.mock(
        side_effect=[
            httpx.Response(200, json={"access_token": "at1", "expires_in": -10}),
            httpx.Response(200, json={"access_token": "at2", "expires_in": 3600}),
        ]
    )
    store = LWATokenStore("c", "s", "r")
    assert store.get_access_token() == "at1"
    assert store.get_access_token() == "at2"  # 已过期，重新刷新
    assert route.call_count == 2
