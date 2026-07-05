from sp_api_mcp.gateway import require_approval, writes_allowed
from sp_api_mcp.tools import feeds


def test_writes_disabled_by_default():
    assert writes_allowed() is False


def test_write_blocked_when_disabled():
    env = feeds.spapi_feeds_create(feed_type="POST_PRODUCT_DATA", content="x")
    assert env.ok is False
    assert env.error["blocked"] is True
    assert "approval" in env.error["reason"].lower()


def test_require_approval_allows_when_enabled(monkeypatch):
    monkeypatch.setattr("sp_api_mcp.gateway.writes_allowed", lambda: True)

    @require_approval
    def do_write():
        from sp_api_mcp.models import Envelope

        return Envelope.ok_response({"done": True})

    env = do_write()
    assert env.ok is True
