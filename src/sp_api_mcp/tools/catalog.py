"""目录（US3）。"""

from __future__ import annotations

from ..client import get_default_client
from ..models import Envelope


def spapi_catalog_item(asin: str, marketplace_ids=None, included_data=None):
    params = {"marketplaceIds": marketplace_ids or get_default_client().settings.marketplace_ids_list}
    if included_data:
        params["includedData"] = ",".join(included_data)
    return get_default_client().call("GET", f"/catalog/2022-04-01/items/{asin}", params=params)


def spapi_catalog_search(keywords: str, marketplace_ids=None, included_data=None):
    params = {
        "keywords": keywords,
        "marketplaceIds": marketplace_ids or get_default_client().settings.marketplace_ids_list,
    }
    if included_data:
        params["includedData"] = ",".join(included_data)
    return get_default_client().call("GET", "/catalog/2022-04-01/items", params=params)


__all__ = ["spapi_catalog_item", "spapi_catalog_search"]
