"""FBA 库存（US3）。"""

from __future__ import annotations

from ..client import get_default_client
from ..models import Envelope


def spapi_fba_inventory(
    marketplace_ids=None,
    granularity="Marketplace",
    granularity_id=None,
    next_token=None,
):
    params = {
        "granularityType": granularity,
        "marketplaceIds": marketplace_ids or get_default_client().settings.marketplace_ids_list,
    }
    if granularity_id:
        params["granularityId"] = granularity_id
    if next_token:
        params["nextToken"] = next_token
    return get_default_client().call(
        "GET", "/fba/inventory/v1/summaries", params=params
    )


__all__ = ["spapi_fba_inventory"]
