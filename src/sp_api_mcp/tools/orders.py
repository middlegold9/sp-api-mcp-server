"""订单工具（US1/US2）。含 PII 接口的 RDT 保护。"""

from __future__ import annotations

from ..client import get_default_client
from ..models import Envelope


def spapi_orders_list(
    marketplace_ids=None,
    created_after=None,
    created_before=None,
    order_statuses=None,
    next_token=None,
    max_results=100,
):
    params = {"MarketplaceIds": marketplace_ids or get_default_client().settings.marketplace_ids_list}
    if created_after:
        params["CreatedAfter"] = created_after
    if created_before:
        params["CreatedBefore"] = created_before
    if order_statuses:
        params["OrderStatuses"] = order_statuses
    if next_token:
        params["NextToken"] = next_token
    params["MaxResultsPerPage"] = max_results
    return get_default_client().call("GET", "/orders/v0/orders", params=params)


def spapi_orders_get(order_id: str):
    return get_default_client().call("GET", f"/orders/v0/orders/{order_id}")


def spapi_orders_items(order_id: str):
    return get_default_client().call("GET", f"/orders/v0/orders/{order_id}/items")


def spapi_orders_buyer_info(order_id: str):
    return get_default_client().call(
        "GET",
        f"/orders/v0/orders/{order_id}/buyerInfo",
        use_rdt=True,
        data_elements=["buyerInfo"],
        operation="getOrderBuyerInfo",
    )


def spapi_orders_address(order_id: str):
    return get_default_client().call(
        "GET",
        f"/orders/v0/orders/{order_id}/address",
        use_rdt=True,
        data_elements=["shippingAddress"],
        operation="getOrderAddress",
    )


__all__ = [
    "spapi_orders_list",
    "spapi_orders_get",
    "spapi_orders_items",
    "spapi_orders_buyer_info",
    "spapi_orders_address",
]
