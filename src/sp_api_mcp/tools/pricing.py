"""价格（US3）。"""

from __future__ import annotations

from ..client import get_default_client
from ..models import Envelope


def spapi_pricing_get(asins, marketplace_id=None):
    marketplace_id = marketplace_id or get_default_client().settings.marketplace_ids_list[0]
    params = {"Asins": ",".join(asins) if isinstance(asins, list) else asins, "ItemType": "Asin", "MarketplaceId": marketplace_id}
    return get_default_client().call("GET", "/products/pricing/v0/priceForASIN", params=params)


def spapi_pricing_competitive(asins, marketplace_id=None):
    marketplace_id = marketplace_id or get_default_client().settings.marketplace_ids_list[0]
    params = {"Asins": ",".join(asins) if isinstance(asins, list) else asins, "ItemType": "Asin", "MarketplaceId": marketplace_id}
    return get_default_client().call("GET", "/products/pricing/v0/competitivePriceForASIN", params=params)


__all__ = ["spapi_pricing_get", "spapi_pricing_competitive"]
