"""测试夹具：注入最小可用 env，避免真实网络/密钥。"""

import os

import pytest

# 在所有测试导入前设置最小 env
os.environ.setdefault("LWA_CLIENT_ID", "test-client")
os.environ.setdefault("LWA_CLIENT_SECRET", "test-secret")
os.environ.setdefault("LWA_REFRESH_TOKEN", "test-refresh")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "AKIA_TEST")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "secret")
os.environ.setdefault("SP_API_ENDPOINT", "https://sellingpartnerapi-na.amazon.com")
os.environ.setdefault("MARKETPLACE_IDS", "ATVPDKIKX0DER")
os.environ.setdefault("APPROVE_WRITES", "false")
os.environ.setdefault("ADS_CLIENT_ID", "ads-client")
os.environ.setdefault("ADS_CLIENT_SECRET", "ads-secret")
os.environ.setdefault("ADS_REFRESH_TOKEN", "ads-refresh")


@pytest.fixture(autouse=True)
def _reset_state():
    from sp_api_mcp.config import get_settings
    from sp_api_mcp import client as client_mod
    from sp_api_mcp.tools import advertising as adv_mod

    get_settings.cache_clear()
    client_mod._DEFAULT = None
    adv_mod._DEFAULT_ADS = None
    yield
    get_settings.cache_clear()
    client_mod._DEFAULT = None
    adv_mod._DEFAULT_ADS = None
