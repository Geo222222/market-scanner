"""Application settings for the market scanner service."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed runtime configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="SCANNER_",
        env_file=".env",
        case_sensitive=False,
    )

    exchange: str = Field(default="htx", description="Primary derivatives exchange identifier (CCXT id).")
    min_qvol_usdt: int = Field(default=20_000_000, description="Minimum 24h quote volume threshold in USDT.")
    max_spread_bps: int = Field(default=8, description="Maximum allowed mid-market spread in basis points.")
    notional_test: int = Field(default=5_000, description="Default notional used for slippage estimations.")
    timeframe: str = Field(default="1m", description="Candle timeframe used for OHLCV pulls.")
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis connection string.")
    postgres_url: Optional[str] = Field(
        default="postgresql+psycopg://scanner:scanner@postgres:5432/scanner",
        description="SQLAlchemy URL (psycopg driver) for persistence.",
    )
    topn_default: int = Field(default=12, description="Default number of symbols returned by ranking endpoints.")
    profile_default: str = Field(default="scalp", description="Fallback scoring profile for rankings.")
    include_carry: bool = Field(default=True, description="Whether to include carry inputs (funding/basis) in scoring.")

    scan_interval_sec: int = Field(default=15, validation_alias=AliasChoices("scan_interval_sec", "scan_interval_s"))
    markets_cache_ttl_sec: int = Field(default=600, validation_alias=AliasChoices("markets_cache_ttl_sec", "markets_cache_ttl_s"))
    adapter_timeout_sec: float = Field(default=8.0, validation_alias=AliasChoices("adapter_timeout_sec", "adapter_timeout_s"))
    adapter_max_failures: int = Field(default=5, description="Failures before the adapter circuit opens.")
    adapter_cooldown_sec: float = Field(default=30.0, validation_alias=AliasChoices("adapter_cooldown_sec", "adapter_cooldown_s"))
    redis_snapshots_ttl_sec: int = Field(default=90, validation_alias=AliasChoices("redis_snapshots_ttl_sec", "redis_snapshots_ttl_s"))
    redis_rankings_ttl_sec: int = Field(default=60, validation_alias=AliasChoices("redis_rankings_ttl_sec", "redis_rankings_ttl_s"))
    scan_concurrency: int = Field(default=12, description="Maximum concurrent CCXT calls during scan.")
    scan_top_by_qvol: int = Field(default=60, description="Number of symbols to retain by quote volume before ranking.")

    metrics_enabled: bool = Field(default=True, description="Expose Prometheus metrics endpoint.")

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
