#!/usr/bin/env python3
"""Test runner for trading system tests."""
import sys
import subprocess
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def run_tests():
    """Run all trading system tests."""
    print("🧪 Running Trading System Tests")
    print("=" * 50)
    
    # Test categories
    test_categories = [
        ("Trading Engine", "test_trading_engine.py"),
        ("Trading Router", "test_trading_router.py"),
        ("Backtesting Engine", "test_backtesting_engine.py"),
        ("Backtesting Router", "test_backtesting_router.py"),
        ("Integration Tests", "test_trading_integration.py"),
        ("Test Configuration", "test_trading_config.py"),
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category, test_file in test_categories:
        print(f"\n📋 Running {category} Tests...")
        print("-" * 30)
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", f"tests/{test_file}", "-v", "--tb=short"],
                cwd=ROOT,
                capture_output=True,
                text=True
            )
            
            # Parse output for test counts
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if "passed" in line and "failed" in line:
                    # Extract numbers from line like "5 passed, 1 failed in 0.12s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed":
                            passed = int(parts[i-1])
                            passed_tests += passed
                        elif part == "failed":
                            failed = int(parts[i-1])
                            failed_tests += failed
                    break
            
            if result.returncode == 0:
                print(f"✅ {category} tests passed")
            else:
                print(f"❌ {category} tests failed")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
                
        except Exception as e:
            print(f"❌ Error running {category} tests: {e}")
            failed_tests += 1
    
    # Summary
    total_tests = passed_tests + failed_tests
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "No tests run")
    
    if failed_tests > 0:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
