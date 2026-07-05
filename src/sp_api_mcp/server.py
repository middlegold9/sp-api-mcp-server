"""FastMCP 入口：注册 T1-T8 全部工具。

运行：
    python -m sp_api_mcp --transport stdio
    python -m sp_api_mcp --transport sse
"""

from __future__ import annotations

import argparse

from mcp.server.fastmcp import FastMCP

from .tools import advertising as adv
from .tools import catalog, feeds, inventory, orders, pricing, reports

mcp = FastMCP("sp-api-mcp")


def _reg(fn):
    mcp.tool()(fn)
    return fn


# 订单
@_reg
def spapi_orders_list(marketplace_ids=None, created_after=None, created_before=None,
                      order_statuses=None, next_token=None, max_results=100):
    return orders.spapi_orders_list(marketplace_ids, created_after, created_before,
                                    order_statuses, next_token, max_results).model_dump()

@_reg
def spapi_orders_get(order_id: str):
    return orders.spapi_orders_get(order_id).model_dump()

@_reg
def spapi_orders_items(order_id: str):
    return orders.spapi_orders_items(order_id).model_dump()

@_reg
def spapi_orders_buyer_info(order_id: str):
    return orders.spapi_orders_buyer_info(order_id).model_dump()

@_reg
def spapi_orders_address(order_id: str):
    return orders.spapi_orders_address(order_id).model_dump()

# 报表 / 库存 / 价格 / 目录
@_reg
def spapi_reports_create(report_type: str, marketplace_ids=None, data_start_time=None,
                         data_end_time=None, report_options=None):
    return reports.spapi_reports_create(report_type, marketplace_ids, data_start_time,
                                        data_end_time, report_options).model_dump()

@_reg
def spapi_reports_get(report_id: str):
    return reports.spapi_reports_get(report_id).model_dump()

@_reg
def spapi_reports_document(report_id: str):
    return reports.spapi_reports_document(report_id).model_dump()

@_reg
def spapi_fba_inventory(marketplace_ids=None, granularity="Marketplace", granularity_id=None,
                        next_token=None):
    return inventory.spapi_fba_inventory(marketplace_ids, granularity, granularity_id,
                                         next_token).model_dump()

@_reg
def spapi_pricing_get(asins, marketplace_id=None):
    return pricing.spapi_pricing_get(asins, marketplace_id).model_dump()

@_reg
def spapi_pricing_competitive(asins, marketplace_id=None):
    return pricing.spapi_pricing_competitive(asins, marketplace_id).model_dump()

@_reg
def spapi_catalog_item(asin: str, marketplace_ids=None, included_data=None):
    return catalog.spapi_catalog_item(asin, marketplace_ids, included_data).model_dump()

@_reg
def spapi_catalog_search(keywords: str, marketplace_ids=None, included_data=None):
    return catalog.spapi_catalog_search(keywords, marketplace_ids, included_data).model_dump()

# Feed
@_reg
def spapi_feeds_get(feed_id: str):
    return feeds.spapi_feeds_get(feed_id).model_dump()

@_reg
def spapi_feeds_document(feed_id: str):
    return feeds.spapi_feeds_document(feed_id).model_dump()

@_reg
def spapi_feeds_create(feed_type: str, content: str, content_type="text/plain; charset=utf-8",
                       marketplace_ids=None):
    return feeds.spapi_feeds_create(feed_type, content, content_type, marketplace_ids).model_dump()

# 广告
@_reg
def ads_profiles_list():
    return adv.ads_profiles_list().model_dump()

@_reg
def ads_campaigns_list(profile_id: str):
    return adv.ads_campaigns_list(profile_id).model_dump()

@_reg
def ads_performance_report(profile_id: str, record_type="campaigns", metrics=None,
                           report_date=None):
    return adv.ads_performance_report(profile_id, record_type, metrics, report_date).model_dump()

@_reg
def ads_searchterms_report(profile_id: str, report_date: str, metrics=None):
    return adv.ads_searchterms_report(profile_id, report_date, metrics).model_dump()


def main():
    parser = argparse.ArgumentParser(prog="sp_api_mcp")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.transport == "sse":
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
