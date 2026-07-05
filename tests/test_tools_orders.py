import httpx
import respx

from sp_api_mcp.tools import orders

TOKEN = "https://api.amazon.com/auth/o2/token"
RDT = "https://api.amazon.com/tokens/2021-03-01/restrictedDataToken"
BASE = "https://sellingpartnerapi-na.amazon.com"


@respx.mock
def test_orders_list():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    respx.get(BASE + "/orders/v0/orders").mock(
        return_value=httpx.Response(200, json={"payload": {"Orders": [{"AmazonOrderId": "111"}]}})
    )
    env = orders.spapi_orders_list(created_after="2024-01-01T00:00:00Z")
    assert env.ok is True
    assert env.data["payload"]["Orders"][0]["AmazonOrderId"] == "111"


@respx.mock
def test_orders_buyer_info_uses_rdt():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    rdt_route = respx.post(RDT).mock(
        return_value=httpx.Response(200, json={"restrictedDataToken": "rdt-x"})
    )
    info_route = respx.get(BASE + "/orders/v0/orders/123/buyerInfo").mock(
        return_value=httpx.Response(200, json={"payload": {"BuyerEmail": "a@b.com"}})
    )
    env = orders.spapi_orders_buyer_info("123")
    assert env.ok is True
    assert rdt_route.called
    # 真实请求应携带 RDT 作为 Bearer
    assert info_route.calls.last.request.headers["x-amz-access-token"] == "rdt-x"
