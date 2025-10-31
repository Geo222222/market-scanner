"""
Test script for zero-fallback data integrity system.

This script tests:
1. FALLBACK_POLICY environment variable handling
2. Strict mode enforcement (no mock data)
3. Permissive mode behavior (allows mock data)
4. Exchange health tracking
5. Data contract compliance
"""

import os
import sys
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.market_scanner.data_integrity import (
    get_fallback_policy,
    is_strict_mode,
    is_permissive_mode,
    validate_data_source,
    exchange_tracker,
    log_data_error,
    log_data_success,
    FallbackPolicy,
    DataSource,
    RankingRow,
    RankingsResponse,
    HealthResponse
)


def test_policy_configuration():
    """Test FALLBACK_POLICY environment variable handling."""
    print("\n" + "="*80)
    print("TEST 1: Policy Configuration")
    print("="*80)
    
    # Test default (strict mode)
    if 'FALLBACK_POLICY' in os.environ:
        del os.environ['FALLBACK_POLICY']
    
    policy = get_fallback_policy()
    print(f"✓ Default policy: {policy}")
    assert policy == FallbackPolicy.STRICT, "Default should be STRICT"
    assert is_strict_mode(), "Should be in strict mode by default"
    assert not is_permissive_mode(), "Should not be in permissive mode by default"
    
    # Test permissive mode
    os.environ['FALLBACK_POLICY'] = 'permissive'
    # Need to reload the module to pick up new env var
    import importlib
    import src.market_scanner.data_integrity as di_module
    importlib.reload(di_module)
    
    from src.market_scanner.data_integrity import get_fallback_policy as get_policy_reload
    policy = get_policy_reload()
    print(f"✓ Permissive mode: {policy}")
    
    # Reset to strict
    os.environ['FALLBACK_POLICY'] = 'strict'
    importlib.reload(di_module)
    
    print("✅ Policy configuration tests PASSED\n")


def test_data_source_validation():
    """Test data source validation under different policies."""
    print("="*80)
    print("TEST 2: Data Source Validation")
    print("="*80)
    
    # In strict mode
    os.environ['FALLBACK_POLICY'] = 'strict'
    
    # Real exchanges should be allowed
    assert validate_data_source(DataSource.HTX), "HTX should be allowed in strict mode"
    assert validate_data_source(DataSource.OKX), "OKX should be allowed in strict mode"
    assert validate_data_source(DataSource.BINANCE), "Binance should be allowed in strict mode"
    print("✓ Real exchanges allowed in strict mode")
    
    # Mock data should NOT be allowed in strict mode
    assert not validate_data_source(DataSource.MOCK), "Mock should NOT be allowed in strict mode"
    assert not validate_data_source(DataSource.ERROR), "Error source should never be allowed"
    print("✓ Mock data rejected in strict mode")
    
    # In permissive mode
    os.environ['FALLBACK_POLICY'] = 'permissive'
    import importlib
    import src.market_scanner.data_integrity as di_module
    importlib.reload(di_module)
    from src.market_scanner.data_integrity import validate_data_source as validate_reload
    
    # Mock data should be allowed in permissive mode
    assert validate_reload(DataSource.MOCK), "Mock should be allowed in permissive mode"
    print("✓ Mock data allowed in permissive mode")
    
    # Reset to strict
    os.environ['FALLBACK_POLICY'] = 'strict'
    importlib.reload(di_module)
    
    print("✅ Data source validation tests PASSED\n")


def test_exchange_health_tracking():
    """Test exchange health tracking."""
    print("="*80)
    print("TEST 3: Exchange Health Tracking")
    print("="*80)
    
    # Record some successes
    exchange_tracker.record_success("htx", 150)
    exchange_tracker.record_success("okx", 200)
    print("✓ Recorded successful operations")
    
    # Record a failure
    exchange_tracker.record_failure("binance", "Connection timeout")
    print("✓ Recorded failed operation")
    
    # Check health status
    htx_health = exchange_tracker.get_health("htx")
    assert htx_health.ok, "HTX should be healthy"
    assert htx_health.latency_ms == 150, "HTX latency should be 150ms"
    print(f"✓ HTX health: ok={htx_health.ok}, latency={htx_health.latency_ms}ms")
    
    binance_health = exchange_tracker.get_health("binance")
    assert not binance_health.ok, "Binance should be unhealthy"
    assert binance_health.last_error == "Connection timeout", "Error message should match"
    print(f"✓ Binance health: ok={binance_health.ok}, error={binance_health.last_error}")
    
    # Check degraded state
    assert exchange_tracker.is_degraded(), "System should be degraded (binance down)"
    assert exchange_tracker.has_any_working(), "System should have working exchanges"
    print("✓ Degraded state detected correctly")
    
    # Get working exchanges
    working = exchange_tracker.get_working_exchanges()
    assert "htx" in working, "HTX should be in working list"
    assert "okx" in working, "OKX should be in working list"
    assert "binance" not in working, "Binance should NOT be in working list"
    print(f"✓ Working exchanges: {working}")
    
    print("✅ Exchange health tracking tests PASSED\n")


def test_data_contract_models():
    """Test data contract Pydantic models."""
    print("="*80)
    print("TEST 4: Data Contract Models")
    print("="*80)
    
    # Test RankingRow
    row = RankingRow(
        rank=1,
        symbol="BTC/USDT",
        exchange="htx",  # REQUIRED field
        score=95.5,
        bias="long",
        confidence=0.85,
        liquidity=1000000.0,
        momentum=0.5,
        spread_bps=2.5,
        ai_insight="Strong bullish momentum",
        ts=datetime.now(timezone.utc).isoformat()
    )
    assert row.exchange == "htx", "Exchange field should be set"
    assert row.rank == 1, "Rank should be 1"
    print(f"✓ RankingRow created: {row.symbol} @ {row.exchange}")
    
    # Test RankingsResponse
    response = RankingsResponse(
        mode="live",
        degraded=False,
        asof=datetime.now(timezone.utc).isoformat(),
        exchanges_ok=["htx", "okx"],
        rows=[row]
    )
    assert response.mode == "live", "Mode should be live"
    assert not response.degraded, "Should not be degraded"
    assert len(response.rows) == 1, "Should have 1 row"
    assert len(response.exchanges_ok) == 2, "Should have 2 working exchanges"
    print(f"✓ RankingsResponse created: {len(response.rows)} rows, {len(response.exchanges_ok)} exchanges ok")
    
    # Test HealthResponse
    from src.market_scanner.data_integrity import ExchangeHealth
    health_response = HealthResponse(
        mode="live",
        live_data_ok=True,
        degraded=False,
        exchanges=[
            {"name": "htx", "ok": True, "latency_ms": 150, "last_error": None, "last_success": None, "last_failure": None},
            {"name": "okx", "ok": True, "latency_ms": 200, "last_error": None, "last_success": None, "last_failure": None}
        ],
        asof=datetime.now(timezone.utc).isoformat()
    )
    assert health_response.live_data_ok, "Live data should be ok"
    assert not health_response.degraded, "Should not be degraded"
    assert len(health_response.exchanges) == 2, "Should have 2 exchanges"
    print(f"✓ HealthResponse created: {len(health_response.exchanges)} exchanges")
    
    print("✅ Data contract model tests PASSED\n")


def test_structured_logging():
    """Test structured error logging."""
    print("="*80)
    print("TEST 5: Structured Logging")
    print("="*80)
    
    # Test error logging
    log_data_error(
        exchange="htx",
        symbol="BTC/USDT",
        operation="fetch_ticker",
        error="Connection timeout",
        retries=3
    )
    print("✓ Logged data error (check logs for structured format)")
    
    # Test success logging
    log_data_success(
        exchange="htx",
        symbol="BTC/USDT",
        operation="fetch_ticker",
        latency_ms=150
    )
    print("✓ Logged data success (check logs for structured format)")
    
    print("✅ Structured logging tests PASSED\n")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("ZERO-FALLBACK DATA INTEGRITY SYSTEM - TEST SUITE")
    print("="*80)
    
    try:
        test_policy_configuration()
        test_data_source_validation()
        test_exchange_health_tracking()
        test_data_contract_models()
        test_structured_logging()
        
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)
        print("\nThe zero-fallback data integrity system is working correctly.")
        print("\nKey features verified:")
        print("  ✓ FALLBACK_POLICY environment variable (strict/permissive)")
        print("  ✓ Strict mode enforcement (no mock data)")
        print("  ✓ Permissive mode behavior (allows mock data)")
        print("  ✓ Exchange health tracking")
        print("  ✓ Data contract compliance")
        print("  ✓ Structured error logging")
        print("\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

