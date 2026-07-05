import httpx
import respx

from sp_api_mcp.auth.lwa import LWATokenStore

TOKEN = "https://api.amazon.com/auth/o2/token"
RDT = "https://api.amazon.com/tokens/2021-03-01/restrictedDataToken"


@respx.mock
def test_mint_rdt():
    respx.post(TOKEN).mock(
        return_value=httpx.Response(200, json={"access_token": "at", "expires_in": 3600})
    )
    rdt_route = respx.post(RDT).mock(
        return_value=httpx.Response(200, json={"restrictedDataToken": "rdt-abc"})
    )
    store = LWATokenStore("c", "s", "r")
    tok = store.mint_rdt(
        operation="getOrderBuyerInfo",
        path="/orders/v0/orders/123/buyerInfo",
        method="GET",
        data_elements=["buyerInfo"],
    )
    assert tok == "rdt-abc"
    assert rdt_route.called
    body = rdt_route.calls.last.request.read().decode()
    assert "getOrderBuyerInfo" in body
    assert "buyerInfo" in body
