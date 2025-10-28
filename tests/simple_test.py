#!/usr/bin/env python3
"""
Simple test runner for Nexus Alpha
"""
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_tests():
    """Run all tests with proper path setup"""
    print("Running Nexus Alpha Tests")
    print("=" * 50)
    
    # Test individual components
    test_modules = [
        "src.core.scoring",
        "src.core.metrics", 
        "src.core.factors",
        "src.engine.momentum",
        "src.engine.microstructure",
        "src.manip.detector",
        "src.adapters.ccxt_adapter",
        "src.stores.redis_store",
        "src.stores.pg_store",
        "src.routers.health",
        "src.routers.rankings",
        "src.routers.opportunities",
        "src.routers.dashboard",
    ]
    
    results = []
    
    for module in test_modules:
        print(f"\nTesting {module}...")
        try:
            # Try to import the module
            __import__(module)
            print(f"PASS - {module} - Import successful")
            results.append((module, "PASS", "Import successful"))
        except Exception as e:
            print(f"FAIL - {module} - Import failed: {e}")
            results.append((module, "FAIL", str(e)))
    
    # Test API endpoints
    print(f"\nTesting API endpoints...")
    try:
        from src.app import app
        print("PASS - FastAPI app - Import successful")
        results.append(("FastAPI App", "PASS", "Import successful"))
    except Exception as e:
        print(f"FAIL - FastAPI app - Import failed: {e}")
        results.append(("FastAPI App", "FAIL", str(e)))
    
    # Test configuration
    print(f"\nTesting configuration...")
    try:
        from src.config import get_settings
        settings = get_settings()
        print(f"PASS - Configuration - Loaded successfully")
        print(f"   Exchange: {settings.exchange}")
        print(f"   Redis URL: {settings.redis_url}")
        print(f"   Min QVol: {settings.min_qvol_usdt}")
        results.append(("Configuration", "PASS", "Loaded successfully"))
    except Exception as e:
        print(f"FAIL - Configuration - Load failed: {e}")
        results.append(("Configuration", "FAIL", str(e)))
    
    # Test templates
    print(f"\nTesting templates...")
    template_files = [
        "src/templates/nexus-dashboard.html",
        "src/templates/panel.html", 
        "src/templates/trading.html"
    ]
    
    for template in template_files:
        if Path(template).exists():
            print(f"PASS - {template} - Found")
            results.append((template, "PASS", "File exists"))
        else:
            print(f"FAIL - {template} - Not found")
            results.append((template, "FAIL", "File not found"))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, status, _ in results if status == "PASS")
    failed = sum(1 for _, status, _ in results if status == "FAIL")
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if failed > 0:
        print(f"\nFAILED TESTS:")
        for module, status, error in results:
            if status == "FAIL":
                print(f"  - {module}: {error}")
    
    print(f"\nFrontend Testing")
    print("=" * 30)
    print("To test the frontend:")
    print("1. Start the server: docker compose up --build -d")
    print("2. Open: http://localhost:8010/dashboard")
    print("3. Check: http://localhost:8010/panel")
    print("4. API: http://localhost:8010/rankings?top=5")
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
