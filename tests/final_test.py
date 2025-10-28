#!/usr/bin/env python3
"""
Final test for Nexus Alpha
"""
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_components():
    """Test individual components"""
    print("Testing Nexus Alpha Components")
    print("=" * 40)
    
    components = [
        ("Core Scoring", "src.core.scoring"),
        ("Core Metrics", "src.core.metrics"),
        ("Core Factors", "src.core.factors"),
        ("Momentum Engine", "src.engine.momentum"),
        ("Microstructure", "src.engine.microstructure"),
        ("Manipulation Detection", "src.manip.detector"),
        ("CCXT Adapter", "src.adapters.ccxt_adapter"),
        ("Redis Store", "src.stores.redis_store"),
        ("PostgreSQL Store", "src.stores.pg_store"),
        ("Health Router", "src.routers.health"),
        ("Rankings Router", "src.routers.rankings"),
        ("Opportunities Router", "src.routers.opportunities"),
        ("Dashboard Router", "src.routers.dashboard"),
    ]
    
    passed = 0
    total = len(components)
    
    for name, module in components:
        try:
            __import__(module)
            print(f"PASS - {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL - {name}: {str(e)[:50]}...")
    
    return passed, total

def test_configuration():
    """Test configuration loading"""
    print("\nTesting Configuration")
    print("=" * 40)
    
    try:
        from src.config import get_settings
        settings = get_settings()
        
        print(f"PASS - Configuration loaded")
        print(f"  Exchange: {settings.exchange}")
        print(f"  Redis URL: {settings.redis_url}")
        print(f"  Min QVol: {settings.min_qvol_usdt:,}")
        print(f"  Max Spread: {settings.max_spread_bps} bps")
        print(f"  Trading Enabled: {settings.trading_enabled}")
        
        return True
    except Exception as e:
        print(f"FAIL - Configuration: {e}")
        return False

def test_templates():
    """Test frontend templates"""
    print("\nTesting Frontend Templates")
    print("=" * 40)
    
    templates = [
        "src/templates/nexus-dashboard.html",
        "src/templates/panel.html",
        "src/templates/trading.html"
    ]
    
    passed = 0
    total = len(templates)
    
    for template in templates:
        if Path(template).exists():
            size = Path(template).stat().st_size
            print(f"PASS - {template} ({size:,} bytes)")
            passed += 1
        else:
            print(f"FAIL - {template} not found")
    
    return passed, total

def test_api_structure():
    """Test API structure without importing app"""
    print("\nTesting API Structure")
    print("=" * 40)
    
    try:
        # Test individual routers
        from src.routers import health, rankings, opportunities, dashboard
        
        print("PASS - Health router imported")
        print("PASS - Rankings router imported") 
        print("PASS - Opportunities router imported")
        print("PASS - Dashboard router imported")
        
        return True
    except Exception as e:
        print(f"FAIL - API structure: {e}")
        return False

def main():
    """Run all tests"""
    print("Nexus Alpha - Final Test Suite")
    print("=" * 50)
    
    # Run tests
    comp_passed, comp_total = test_components()
    config_ok = test_configuration()
    temp_passed, temp_total = test_templates()
    api_ok = test_api_structure()
    
    # Calculate overall results
    total_tests = comp_total + 1 + temp_total + 1  # +1 for config and api
    total_passed = comp_passed + (1 if config_ok else 0) + temp_passed + (1 if api_ok else 0)
    
    # Summary
    print("\n" + "=" * 50)
    print("FINAL TEST SUMMARY")
    print("=" * 50)
    
    print(f"Components:     {comp_passed}/{comp_total} passed")
    print(f"Configuration:  {'PASS' if config_ok else 'FAIL'}")
    print(f"Templates:      {temp_passed}/{temp_total} passed")
    print(f"API Structure:  {'PASS' if api_ok else 'FAIL'}")
    print("-" * 50)
    print(f"Overall:        {total_passed}/{total_tests} passed ({(total_passed/total_tests)*100:.1f}%)")
    
    if total_passed == total_tests:
        print("\nSUCCESS: All tests passed!")
        print("\nNexus Alpha is ready for use!")
        print("\nTo start the application:")
        print("1. Ensure Docker Desktop is running")
        print("2. Run: docker compose up --build -d")
        print("3. Open: http://localhost:8010/dashboard")
        print("4. Alternative: http://localhost:8010/panel")
        print("5. API test: http://localhost:8010/rankings?top=5")
    else:
        print(f"\nWARNING: {total_tests - total_passed} tests failed")
        print("Please check the issues above before proceeding")
    
    return total_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
