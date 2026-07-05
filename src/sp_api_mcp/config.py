"""配置：从 .env 读取 SP-API / Ads / 行为开关。"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding="utf-8")

    # LWA (SP-API)
    lwa_client_id: str = ""
    lwa_client_secret: str = ""
    lwa_refresh_token: str = ""

    # AWS SigV4
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"  # SigV4 签名区域

    # SP-API 端点（按 marketplace 分区）
    sp_api_endpoint: str = "https://sellingpartnerapi-na.amazon.com"
    sp_api_region: str = "us-east-1"

    # 行为
    cache_ttl: int = 300
    marketplace_ids: str = "ATVPDKIKX0DER"  # 逗号分隔
    approve_writes: bool = False  # 写工具（Feed / 广告调价）审批网关总开关

    # Ads API（独立 OAuth）
    ads_client_id: str = ""
    ads_client_secret: str = ""
    ads_refresh_token: str = ""
    ads_endpoint: str = "https://advertising-api.amazon.com"
    ads_oauth_endpoint: str = "https://api.amazon.com/auth/o2/token"

    @property
    def marketplace_ids_list(self) -> list[str]:
        return [m.strip() for m in self.marketplace_ids.split(",") if m.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
