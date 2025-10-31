#!/usr/bin/env python3
"""
Test script to verify logging configuration is working correctly.

This script tests:
1. WebSocket logger suppression
2. CCXT logger suppression
3. Application logger visibility
4. File vs console output
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from market_scanner.logging_config import configure_production_logging, get_logger


def test_logging_configuration():
    """Test the logging configuration."""
    
    print("\n" + "=" * 70)
    print("TESTING LOGGING CONFIGURATION")
    print("=" * 70 + "\n")
    
    # Configure logging
    print("1. Configuring production logging...")
    configure_production_logging(
        log_level="INFO",
        enable_file_logging=False,  # Disable file logging for this test
        enable_console_logging=True
    )
    
    print("\n2. Testing application loggers (SHOULD APPEAR)...")
    print("-" * 70)
    
    app_logger = get_logger("market_scanner.test")
    app_logger.info("✅ Application INFO message")
    app_logger.warning("✅ Application WARNING message")
    app_logger.error("✅ Application ERROR message")
    
    print("\n3. Testing application DEBUG messages (SHOULD NOT APPEAR in console)...")
    print("-" * 70)
    app_logger.debug("❌ Application DEBUG message (should not appear)")
    print("(If you see a DEBUG message above, configuration failed)")
    
    print("\n4. Testing WebSocket logger suppression (SHOULD NOT APPEAR)...")
    print("-" * 70)
    
    ws_logger = logging.getLogger("websockets.client")
    ws_logger.debug("❌ WebSocket DEBUG: < BINARY 1f 8b 08 00 (should not appear)")
    ws_logger.info("❌ WebSocket INFO: Connection established (should not appear)")
    ws_logger.warning("✅ WebSocket WARNING: Connection lost (should appear)")
    
    print("\n5. Testing CCXT logger suppression (SHOULD NOT APPEAR)...")
    print("-" * 70)
    
    ccxt_logger = logging.getLogger("ccxt.base")
    ccxt_logger.debug("❌ CCXT DEBUG: Request details (should not appear)")
    ccxt_logger.info("❌ CCXT INFO: API call (should not appear)")
    ccxt_logger.warning("✅ CCXT WARNING: Rate limit (should appear)")
    
    print("\n6. Testing other library suppression (SHOULD NOT APPEAR)...")
    print("-" * 70)
    
    urllib_logger = logging.getLogger("urllib3.connectionpool")
    urllib_logger.debug("❌ urllib3 DEBUG: Starting new HTTPS connection (should not appear)")
    urllib_logger.info("❌ urllib3 INFO: Connection info (should not appear)")
    
    aiohttp_logger = logging.getLogger("aiohttp.client")
    aiohttp_logger.debug("❌ aiohttp DEBUG: Request sent (should not appear)")
    aiohttp_logger.info("❌ aiohttp INFO: Response received (should not appear)")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nExpected results:")
    print("  ✅ Application INFO/WARNING/ERROR messages should appear")
    print("  ✅ Library WARNING messages should appear")
    print("  ❌ Application DEBUG messages should NOT appear")
    print("  ❌ Library DEBUG/INFO messages should NOT appear")
    print("\nIf you see any ❌ messages above (except in descriptions), the test failed.")
    print("=" * 70 + "\n")


def test_ccxt_verbose():
    """Test CCXT verbose flag."""
    
    print("\n" + "=" * 70)
    print("TESTING CCXT VERBOSE FLAG")
    print("=" * 70 + "\n")
    
    try:
        import ccxt
        
        print("1. Creating CCXT exchange with verbose=False...")
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'verbose': False
        })
        
        print(f"   Exchange verbose setting: {exchange.verbose}")
        
        if exchange.verbose:
            print("   ❌ FAILED: verbose should be False")
        else:
            print("   ✅ PASSED: verbose is False")
        
        print("\n2. Testing set_ccxt_verbose helper...")
        from market_scanner.logging_config import set_ccxt_verbose
        
        # Set to True
        set_ccxt_verbose(exchange, verbose=True)
        print(f"   After set_ccxt_verbose(True): {exchange.verbose}")
        
        # Set back to False
        set_ccxt_verbose(exchange, verbose=False)
        print(f"   After set_ccxt_verbose(False): {exchange.verbose}")
        
        if not exchange.verbose:
            print("   ✅ PASSED: set_ccxt_verbose works correctly")
        else:
            print("   ❌ FAILED: set_ccxt_verbose did not work")
        
    except ImportError:
        print("   ⚠️  SKIPPED: ccxt not installed")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 70 + "\n")


def test_file_logging():
    """Test file logging configuration."""
    
    print("\n" + "=" * 70)
    print("TESTING FILE LOGGING")
    print("=" * 70 + "\n")
    
    # Create temporary log file
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "test_logging.log"
    
    # Remove old test log if exists
    if log_file.exists():
        log_file.unlink()
    
    print(f"1. Configuring logging with file: {log_file}")
    
    # Reconfigure with file logging
    configure_production_logging(
        log_level="INFO",
        log_file=log_file,
        enable_file_logging=True,
        enable_console_logging=False  # Disable console for this test
    )
    
    print("2. Writing test messages...")
    logger = get_logger("market_scanner.file_test")
    logger.debug("DEBUG message (should be in file)")
    logger.info("INFO message (should be in file)")
    logger.warning("WARNING message (should be in file)")
    logger.error("ERROR message (should be in file)")
    
    print("3. Checking log file...")
    
    if log_file.exists():
        content = log_file.read_text()
        lines = content.strip().split('\n')
        
        print(f"   ✅ Log file created: {log_file}")
        print(f"   ✅ Log file has {len(lines)} lines")
        
        # Check for expected messages
        has_debug = any("DEBUG" in line and "DEBUG message" in line for line in lines)
        has_info = any("INFO" in line and "INFO message" in line for line in lines)
        has_warning = any("WARNING" in line and "WARNING message" in line for line in lines)
        has_error = any("ERROR" in line and "ERROR message" in line for line in lines)
        
        if has_debug:
            print("   ✅ DEBUG message found in file")
        else:
            print("   ❌ DEBUG message NOT found in file")
        
        if has_info:
            print("   ✅ INFO message found in file")
        else:
            print("   ❌ INFO message NOT found in file")
        
        if has_warning:
            print("   ✅ WARNING message found in file")
        else:
            print("   ❌ WARNING message NOT found in file")
        
        if has_error:
            print("   ✅ ERROR message found in file")
        else:
            print("   ❌ ERROR message NOT found in file")
        
        print("\n   Sample log lines:")
        for line in lines[-5:]:  # Show last 5 lines
            print(f"   {line}")
        
        # Clean up (close all handlers first on Windows)
        print(f"\n4. Cleaning up test log file...")
        # Close all handlers to release file lock on Windows
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)

        try:
            log_file.unlink()
            print("   ✅ Test log file removed")
        except PermissionError:
            print("   ⚠️  Could not remove test log file (Windows file lock)")
            print(f"   Please manually delete: {log_file}")
        
    else:
        print("   ❌ FAILED: Log file was not created")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("NEXUS ALPHA - LOGGING CONFIGURATION TEST SUITE")
    print("=" * 70)
    
    try:
        # Test 1: Basic logging configuration
        test_logging_configuration()
        
        # Test 2: CCXT verbose flag
        test_ccxt_verbose()
        
        # Test 3: File logging
        test_file_logging()
        
        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETE")
        print("=" * 70)
        print("\nReview the output above to verify:")
        print("  1. Only expected messages appeared in console")
        print("  2. CCXT verbose flag is working")
        print("  3. File logging captures all levels")
        print("\n" + "=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

