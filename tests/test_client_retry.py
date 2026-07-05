import httpx
import respx

from sp_api_mcp.tools import orders

TOKEN = "https://api.amazon.com/auth/o2/token"
ORDERS = "https://sellingpartnerapi-na.amazon.com/orders/v0/orders"


@respx.mock
def test_retry_on_429_then_success():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    route = respx.get(ORDERS).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"payload": {"Orders": []}}),
        ]
    )
    env = orders.spapi_orders_list(created_after="2024-01-01T00:00:00Z")
    assert env.ok is True
    assert route.call_count == 2  # 一次 429 + 一次成功


@respx.mock
def test_rate_remaining_recorded():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    respx.get(ORDERS).mock(
        return_value=httpx.Response(
            200, json={"payload": {}}, headers={"x-amzn-RateLimit-Limit": "1.5"}
        )
    )
    env = orders.spapi_orders_list(created_after="2024-01-01T00:00:00Z")
    assert env.rate_remaining == 1
