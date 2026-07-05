"""报表：创建 / 查询 / 下载（US3）。"""

from __future__ import annotations

from ..client import get_default_client
from ..models import Envelope


def spapi_reports_create(
    report_type: str,
    marketplace_ids=None,
    data_start_time=None,
    data_end_time=None,
    report_options=None,
):
    body = {
        "reportType": report_type,
        "marketplaceIds": marketplace_ids or get_default_client().settings.marketplace_ids_list,
    }
    if data_start_time:
        body["dataStartTime"] = data_start_time
    if data_end_time:
        body["dataEndTime"] = data_end_time
    if report_options:
        body["reportOptions"] = report_options
    return get_default_client().call(
        "POST", "/reports/2021-06-30/reports", json_body=body, skip_cache=True
    )


def spapi_reports_get(report_id: str):
    return get_default_client().call("GET", f"/reports/2021-06-30/reports/{report_id}")


def spapi_reports_document(report_id: str):
    """按 report_id 拉报告状态 -> 取 documentId -> 取下载 url -> 下载（自动解压）。"""
    client = get_default_client()
    rep = client.call("GET", f"/reports/2021-06-30/reports/{report_id}")
    if not rep.ok:
        return rep
    document_id = (rep.data or {}).get("reportDocumentId")
    if not document_id:
        return Envelope.err({"detail": "report not ready / no document", "raw": rep.data})
    doc = client.call("GET", f"/reports/2021-06-30/documents/{document_id}")
    if not doc.ok:
        return doc
    url = (doc.data or {}).get("url")
    if not url:
        return Envelope.err({"detail": "no document url", "raw": doc.data})
    text = client.download_document(url)
    return Envelope.ok_response({"report_id": report_id, "document_id": document_id, "content": text})


__all__ = ["spapi_reports_create", "spapi_reports_get", "spapi_reports_document"]
