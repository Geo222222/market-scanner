"""Application settings for the market scanner service."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed runtime configuration sourced from environment variables."""

    model_config = SettingsConfigDict(env_prefix="SCANNER_", env_file=".env", case_sensitive=False)

    exchange: str = Field(default="binanceusdm", description="Primary derivatives exchange identifier.")
    min_qvol_usdt: int = Field(default=50_000_000, description="Minimum 24h quote volume threshold in USDT.")
    max_spread_bps: int = Field(default=5, description="Maximum allowed mid-market spread in basis points.")
    notional_test: int = Field(default=10_000, description="Default notional used for slippage estimations.")
    timeframe: str = Field(default="1m", description="Candle timeframe used for OHLCV pulls.")
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis connection string.")
    postgres_url: Optional[str] = Field(default=None, description="SQLAlchemy URL (psycopg driver) for persistence.")
    topn_default: int = Field(default=12, description="Default number of symbols returned by ranking endpoints.")
    scan_interval_s: int = Field(default=30, description="Interval between full market scans.")
    markets_cache_ttl_s: int = Field(default=600, description="Lifetime for cached markets metadata.")
    adapter_timeout_s: float = Field(default=8.0, description="Per-request timeout for adapter calls.")
    adapter_max_failures: int = Field(default=5, description="Failures before the adapter circuit opens.")
    adapter_cooldown_s: float = Field(default=30.0, description="Cooldown window when the circuit breaker is open.")
    redis_snapshots_ttl_s: int = Field(default=90, description="TTL for cached symbol snapshots in Redis.")
    redis_rankings_ttl_s: int = Field(default=60, description="TTL for cached rankings payloads in Redis.")
    job_chunk_size: int = Field(default=10, description="Batch size when pulling market data concurrently.")
    ranking_profile_default: str = Field(default="scalp", description="Fallback scoring profile for rankings.")
    symbols: list[str] = Field(default_factory=list, description="Optional static symbol allow-list for legacy routes.")

    @field_validator("postgres_url")
    @classmethod
    def _validate_postgres(cls, value: Optional[str]) -> Optional[str]:
        if value and "psycopg" not in value:
            raise ValueError("POSTGRES_URL must use a psycopg driver, e.g. postgresql+psycopg://...")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance to avoid repeated environment parsing."""

    return Settings()


settings = get_settings()
