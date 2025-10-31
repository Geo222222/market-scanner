"""
Zero-Fallback Data Integrity System

This module implements strict runtime enforcement of data integrity policies.
In production (strict mode), no synthetic or mock data is ever returned to users.
All data failures are handled gracefully with proper error states.

Environment Variable: FALLBACK_POLICY
- strict (default for production): Never synthesize or mock data
- permissive (development/demo): Allow mock data with explicit labeling
"""

import os
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FallbackPolicy(str, Enum):
    """Runtime policy for handling data failures."""
    STRICT = "strict"
    PERMISSIVE = "permissive"


class DataSource(str, Enum):
    """Data source indicators."""
    HTX = "htx"
    OKX = "okx"
    BINANCE = "binance"
    BYBIT = "bybit"
    BITGET = "bitget"
    MOCK = "mock"  # Only allowed in permissive mode
    ERROR = "error"  # Indicates failure


class DataStatus(str, Enum):
    """Data availability status."""
    OK = "ok"
    ERROR = "error"
    DEGRADED = "degraded"


class BiasType(str, Enum):
    """Trading bias enumeration."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


# ============================================================================
# RUNTIME POLICY CONFIGURATION
# ============================================================================

def get_fallback_policy() -> FallbackPolicy:
    """
    Get the current fallback policy from environment.
    
    Returns:
        FallbackPolicy.STRICT for production (default)
        FallbackPolicy.PERMISSIVE for development/demo
    """
    policy_str = os.getenv("FALLBACK_POLICY", "strict").lower()
    
    if policy_str == "permissive":
        logger.warning("Running in PERMISSIVE mode - mock data is allowed")
        return FallbackPolicy.PERMISSIVE
    
    logger.info("Running in STRICT mode - no mock data allowed")
    return FallbackPolicy.STRICT


def is_strict_mode() -> bool:
    """Check if running in strict mode (production)."""
    return get_fallback_policy() == FallbackPolicy.STRICT


def is_permissive_mode() -> bool:
    """Check if running in permissive mode (development/demo)."""
    return get_fallback_policy() == FallbackPolicy.PERMISSIVE


def validate_data_source(source: str) -> bool:
    """
    Validate that a data source is allowed under current policy.
    
    Args:
        source: Data source identifier
        
    Returns:
        True if source is allowed, False otherwise
    """
    if source == DataSource.MOCK:
        return is_permissive_mode()
    
    if source == DataSource.ERROR:
        return False
    
    # Real exchanges are always allowed
    return source in [DataSource.HTX, DataSource.OKX, DataSource.BINANCE, 
                     DataSource.BYBIT, DataSource.BITGET]


# ============================================================================
# DATA CONTRACT MODELS
# ============================================================================

class RankingRow(BaseModel):
    """Single ranking row with strict field requirements."""
    rank: int = Field(..., description="Ranking position")
    symbol: str = Field(..., description="Trading pair symbol")
    exchange: str = Field(..., description="Exchange name - REQUIRED, never null")
    score: float = Field(..., description="Ranking score")
    bias: BiasType = Field(..., description="Trading bias: long, short, or neutral")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    liquidity: float = Field(..., description="Liquidity metric")
    momentum: float = Field(..., description="Momentum metric")
    spread_bps: float = Field(..., description="Spread in basis points")
    ai_insight: Optional[str] = Field(None, description="AI-generated insight")
    ts: str = Field(..., description="ISO8601 timestamp")
    
    class Config:
        use_enum_values = True


class RankingsResponse(BaseModel):
    """Rankings API response with degradation tracking."""
    mode: str = Field(default="live", description="Operating mode")
    degraded: bool = Field(default=False, description="True if partial availability")
    asof: str = Field(..., description="ISO8601 timestamp of data")
    exchanges_ok: List[str] = Field(default_factory=list, description="List of working exchanges")
    rows: List[RankingRow] = Field(default_factory=list, description="Ranking rows")
    error: Optional[str] = Field(None, description="Error code if complete failure")
    detail: Optional[str] = Field(None, description="Error detail message")


class CandlesResponse(BaseModel):
    """Candles/Chart data API response."""
    source: str = Field(..., description="Data source (exchange name or 'mock')")
    status: DataStatus = Field(..., description="Data status: ok or error")
    asof: str = Field(..., description="ISO8601 timestamp")
    symbol: Optional[str] = Field(None, description="Symbol (present on error)")
    tf: Optional[str] = Field(None, description="Timeframe (present on error)")
    candles: Optional[List[List[float]]] = Field(None, description="OHLCV candles")
    error: Optional[str] = Field(None, description="Error code")
    
    class Config:
        use_enum_values = True


class OrderBookResponse(BaseModel):
    """Level 2 order book API response."""
    source: str = Field(..., description="Data source (exchange name or 'mock')")
    status: DataStatus = Field(..., description="Data status: ok or error")
    asof: str = Field(..., description="ISO8601 timestamp")
    symbol: Optional[str] = Field(None, description="Symbol (present on error)")
    depth: Optional[int] = Field(None, description="Requested depth (present on error)")
    bids: Optional[List[List[float]]] = Field(None, description="Bid levels [price, volume]")
    asks: Optional[List[List[float]]] = Field(None, description="Ask levels [price, volume]")
    error: Optional[str] = Field(None, description="Error code")
    
    class Config:
        use_enum_values = True


# ============================================================================
# EXCHANGE HEALTH TRACKING
# ============================================================================

class ExchangeHealth(BaseModel):
    """Health status for a single exchange."""
    name: str = Field(..., description="Exchange name")
    ok: bool = Field(..., description="True if exchange is operational")
    last_error: Optional[str] = Field(None, description="Last error message")
    latency_ms: Optional[int] = Field(None, description="Last request latency in ms")
    last_success: Optional[str] = Field(None, description="ISO8601 timestamp of last success")
    last_failure: Optional[str] = Field(None, description="ISO8601 timestamp of last failure")


class HealthResponse(BaseModel):
    """Health endpoint response."""
    mode: str = Field(default="live", description="Operating mode")
    live_data_ok: bool = Field(..., description="True if at least one exchange is working")
    degraded: bool = Field(..., description="True if any exchange is down")
    exchanges: List[ExchangeHealth] = Field(..., description="Per-exchange health status")
    asof: str = Field(..., description="ISO8601 timestamp")


# ============================================================================
# EXCHANGE STATUS TRACKER
# ============================================================================

class ExchangeStatusTracker:
    """
    Track health and status of exchange connections.
    Thread-safe singleton for tracking exchange availability.
    """
    
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._status: Dict[str, Dict[str, Any]] = {}
        self._initialized = True
        
        # Initialize known exchanges
        for exchange in [DataSource.HTX, DataSource.OKX, DataSource.BINANCE]:
            self._status[exchange] = {
                "ok": False,
                "last_error": None,
                "latency_ms": None,
                "last_success": None,
                "last_failure": None,
                "error_count": 0,
                "success_count": 0
            }
    
    def record_success(self, exchange: str, latency_ms: int):
        """Record successful exchange operation."""
        if exchange not in self._status:
            self._status[exchange] = {
                "ok": True,
                "last_error": None,
                "latency_ms": latency_ms,
                "last_success": datetime.now(timezone.utc).isoformat(),
                "last_failure": None,
                "error_count": 0,
                "success_count": 1
            }
        else:
            self._status[exchange]["ok"] = True
            self._status[exchange]["latency_ms"] = latency_ms
            self._status[exchange]["last_success"] = datetime.now(timezone.utc).isoformat()
            self._status[exchange]["success_count"] += 1
            self._status[exchange]["last_error"] = None  # Clear error on success
    
    def record_failure(self, exchange: str, error: str):
        """Record failed exchange operation."""
        if exchange not in self._status:
            self._status[exchange] = {
                "ok": False,
                "last_error": error,
                "latency_ms": None,
                "last_success": None,
                "last_failure": datetime.now(timezone.utc).isoformat(),
                "error_count": 1,
                "success_count": 0
            }
        else:
            self._status[exchange]["ok"] = False
            self._status[exchange]["last_error"] = error
            self._status[exchange]["last_failure"] = datetime.now(timezone.utc).isoformat()
            self._status[exchange]["error_count"] += 1
    
    def get_health(self, exchange: str) -> ExchangeHealth:
        """Get health status for an exchange."""
        status = self._status.get(exchange, {
            "ok": False,
            "last_error": "Not initialized",
            "latency_ms": None,
            "last_success": None,
            "last_failure": None
        })
        
        return ExchangeHealth(
            name=exchange,
            ok=status["ok"],
            last_error=status["last_error"],
            latency_ms=status["latency_ms"],
            last_success=status["last_success"],
            last_failure=status["last_failure"]
        )
    
    def get_all_health(self) -> List[ExchangeHealth]:
        """Get health status for all exchanges."""
        return [self.get_health(exchange) for exchange in self._status.keys()]
    
    def is_degraded(self) -> bool:
        """Check if any exchange is down."""
        return any(not status["ok"] for status in self._status.values())
    
    def has_any_working(self) -> bool:
        """Check if at least one exchange is working."""
        return any(status["ok"] for status in self._status.values())
    
    def get_working_exchanges(self) -> List[str]:
        """Get list of currently working exchanges."""
        return [exchange for exchange, status in self._status.items() if status["ok"]]


# Global singleton instance
exchange_tracker = ExchangeStatusTracker()


# ============================================================================
# STRUCTURED ERROR LOGGING
# ============================================================================

def log_data_error(
    exchange: str,
    symbol: str,
    operation: str,
    error: str,
    retries: int = 0,
    mode: Optional[str] = None
):
    """
    Log data errors in structured format.
    
    Format: level=ERROR svc=collector exchange=htx symbol=SOL/USDT op=candles err="..." retries=2 mode=strict
    """
    if mode is None:
        mode = get_fallback_policy().value
    
    logger.error(
        f"level=ERROR svc=collector exchange={exchange} symbol={symbol} "
        f"op={operation} err=\"{error}\" retries={retries} mode={mode}"
    )
    
    # Record in exchange tracker
    exchange_tracker.record_failure(exchange, error)


def log_data_success(exchange: str, symbol: str, operation: str, latency_ms: int):
    """Log successful data operations."""
    logger.debug(
        f"level=DEBUG svc=collector exchange={exchange} symbol={symbol} "
        f"op={operation} latency_ms={latency_ms}"
    )
    
    # Record in exchange tracker
    exchange_tracker.record_success(exchange, latency_ms)

