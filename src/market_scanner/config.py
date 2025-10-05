"""Application settings for the market scanner service."""
from __future__ import annotations

from functools import lru_cache
import json
from typing import Optional

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed runtime configuration sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="SCANNER_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
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
    ca_bundle_path: Optional[str] = Field(
        default=None,
        description="Optional path to a CA bundle for outbound HTTPS calls.",
    )
    topn_default: int = Field(default=12, description="Default number of symbols returned by ranking endpoints.")
    profile_default: str = Field(default="scalp", description="Fallback scoring profile for rankings.")
    include_carry: bool = Field(default=True, description="Whether to include carry inputs (funding/basis) in scoring.")

    scan_interval_sec: int = Field(default=15, validation_alias=AliasChoices("scan_interval_sec", "scan_interval_s"))
    scan_sla_warn_multiplier: float = Field(default=2.0, description="Multiplier of target cycle time before warning level.")
    scan_sla_critical_multiplier: float = Field(default=3.0, description="Multiplier of target cycle time before critical level.")
    markets_cache_ttl_sec: int = Field(default=600, validation_alias=AliasChoices("markets_cache_ttl_sec", "markets_cache_ttl_s"))
    adapter_timeout_sec: float = Field(default=90.0)
    adapter_max_failures: int = Field(default=5, description="Failures before the adapter circuit opens.")
    adapter_cooldown_sec: float = Field(default=30.0, validation_alias=AliasChoices("adapter_cooldown_sec", "adapter_cooldown_s"))
    redis_snapshots_ttl_sec: int = Field(default=90, validation_alias=AliasChoices("redis_snapshots_ttl_sec", "redis_snapshots_ttl_s"))
    redis_rankings_ttl_sec: int = Field(default=60, validation_alias=AliasChoices("redis_rankings_ttl_sec", "redis_rankings_ttl_s"))
    scan_concurrency: int = Field(default=12, description="Maximum concurrent CCXT calls during scan.")
    scan_top_by_qvol: int = Field(default=60, description="Number of symbols to retain by quote volume before ranking.")
    symbols: list[str] = Field(default_factory=list, description="Optional static allow list for scanning.")

    raw_retention_hours: int = Field(default=24, description="Retention for raw exchange messages in hours.")
    bar_1s_retention_hours: int = Field(default=72, description="Retention for 1-second bars in hours.")
    bar_5s_retention_days: int = Field(default=14, description="Retention for 5-second bars in days.")
    bar_1m_retention_days: int = Field(default=60, description="Retention for 1-minute bars in days.")

    metrics_enabled: bool = Field(default=True, description="Expose Prometheus metrics endpoint.")
    alert_webhook_url: Optional[str] = Field(default=None, description="Optional webhook for alert fan-out.")
    signal_channel: str = Field(default="scanner.signals", description="Redis pub/sub channel for signals.")

    @field_validator("symbols", mode="before")
    @classmethod
    def _coerce_symbols(cls, value):
        if value in (None, "", [], ( )):
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    value = parsed
                else:
                    value = [raw]
            except json.JSONDecodeError:
                parts = [part.strip() for part in raw.split(',') if part.strip()]
                value = parts or []
        if isinstance(value, (set, tuple)):
            value = list(value)
        if not isinstance(value, list):
            raise ValueError("symbols must be a list of strings")
        normalised = []
        for item in value:
            text_item = str(item).strip()
            if text_item:
                normalised.append(text_item)
        return normalised

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
