"""Feed 写工具 + 审批网关（US4/FR6）。"""

from __future__ import annotations

from ..client import get_default_client
from ..gateway import require_approval
from ..models import Envelope


def spapi_feeds_get(feed_id: str):
    return get_default_client().call("GET", f"/feeds/2021-06-30/feeds/{feed_id}")


def spapi_feeds_document(feed_id: str):
    """拉 feed 状态 -> documentId -> 下载结果文档。"""
    client = get_default_client()
    feed = client.call("GET", f"/feeds/2021-06-30/feeds/{feed_id}")
    if not feed.ok:
        return feed
    document_id = (feed.data or {}).get("resultFeedDocumentId")
    if not document_id:
        return Envelope.err({"detail": "feed not processed / no document", "raw": feed.data})
    doc = client.call("GET", f"/feeds/2021-06-30/documents/{document_id}")
    if not doc.ok:
        return doc
    url = (doc.data or {}).get("url")
    if not url:
        return Envelope.err({"detail": "no document url", "raw": doc.data})
    text = client.download_document(url)
    return Envelope.ok_response({"feed_id": feed_id, "document_id": document_id, "content": text})


@require_approval
def spapi_feeds_create(
    feed_type: str,
    content: str,
    content_type: str = "text/plain; charset=utf-8",
    marketplace_ids=None,
):
    """创建并上传 Feed（写操作，需审批网关开启）。content 为明文，自动 base64。"""
    client = get_default_client()
    body = {
        "feedType": feed_type,
        "marketplaceIds": marketplace_ids or client.settings.marketplace_ids_list,
        "inputFeedDocument": {"contentType": content_type},
    }
    created = client.call("POST", "/feeds/2021-06-30/feeds", json_body=body, skip_cache=True)
    if not created.ok:
        return created
    doc_id = (created.data or {}).get("feedDocumentId")
    if not doc_id:
        return Envelope.err({"detail": "no feedDocumentId", "raw": created.data})
    # 上传文档内容
    doc_meta = client.call("GET", f"/feeds/2021-06-30/documents/{doc_id}")
    if not doc_meta.ok:
        return doc_meta
    upload_url = (doc_meta.data or {}).get("url")
    if not upload_url:
        return Envelope.err({"detail": "no upload url", "raw": doc_meta.data})
    put = client._client.put(upload_url, content=content.encode("utf-8"), headers={"Content-Type": content_type})
    put.raise_for_status()
    return Envelope.ok_response({"feed_id": (created.data or {}).get("feedId"), "feed_document_id": doc_id})


__all__ = ["spapi_feeds_get", "spapi_feeds_document", "spapi_feeds_create"]
