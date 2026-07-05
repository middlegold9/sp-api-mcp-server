from sp_api_mcp.models import Envelope


def test_envelope_ok_serialization():
    env = Envelope.ok_response({"a": 1}, rate_remaining=42)
    assert env.ok is True
    assert env.data == {"a": 1}
    assert env.rate_remaining == 42
    assert env.cached is False
    d = env.model_dump()
    assert d["ok"] is True
    assert "request_id" in d


def test_envelope_err():
    env = Envelope.err({"status": 429, "detail": "slow down"})
    assert env.ok is False
    assert env.error["status"] == 429
    assert env.data is None
