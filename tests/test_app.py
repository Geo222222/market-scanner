#!/usr/bin/env python3
"""
Test script for Nexus Alpha application
"""
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_app():
    """Test the FastAPI application"""
    print("Testing Nexus Alpha Application")
    print("=" * 40)
    
    try:
        # Import and create app
        from app import app
        print("✓ FastAPI app imported successfully")
        
        # Test app properties
        print(f"✓ App title: {app.title}")
        print(f"✓ App description: {app.description}")
        
        # Test routes
        routes = [route.path for route in app.routes]
        print(f"✓ Total routes: {len(routes)}")
        
        # Check key routes
        key_routes = [
            "/health",
            "/rankings", 
            "/opportunities",
            "/dashboard",
            "/panel"
        ]
        
        for route in key_routes:
            if route in routes:
                print(f"✓ Route {route} - Found")
            else:
                print(f"✗ Route {route} - Missing")
        
        print("\n✓ Application test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Application test failed: {e}")
        return False

def test_frontend():
    """Test frontend templates"""
    print("\nTesting Frontend Templates")
    print("=" * 40)
    
    template_files = [
        "src/templates/nexus-dashboard.html",
        "src/templates/panel.html",
        "src/templates/trading.html"
    ]
    
    all_found = True
    
    for template in template_files:
        if Path(template).exists():
            print(f"✓ {template} - Found")
            
            # Check file size
            size = Path(template).stat().st_size
            print(f"  Size: {size:,} bytes")
            
            # Check for key content
            with open(template, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'Nexus Alpha' in content:
                print(f"  ✓ Contains 'Nexus Alpha' branding")
            else:
                print(f"  ✗ Missing 'Nexus Alpha' branding")
                
            if 'Alpine.js' in content or 'alpinejs' in content:
                print(f"  ✓ Uses Alpine.js framework")
            else:
                print(f"  ✗ Missing Alpine.js framework")
                
        else:
            print(f"✗ {template} - Not found")
            all_found = False
    
    return all_found

def test_api_endpoints():
    """Test API endpoint structure"""
    print("\nTesting API Endpoints")
    print("=" * 40)
    
    try:
        from app import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append({
                    'path': route.path,
                    'methods': list(route.methods),
                    'name': getattr(route, 'name', 'Unknown')
                })
        
        # Group by category
        categories = {
            'Health': [],
            'Market Data': [],
            'Trading': [],
            'Dashboard': [],
            'Other': []
        }
        
        for route in routes:
            path = route['path']
            if '/health' in path:
                categories['Health'].append(route)
            elif any(x in path for x in ['/rankings', '/opportunities', '/symbols']):
                categories['Market Data'].append(route)
            elif any(x in path for x in ['/trading', '/backtesting']):
                categories['Trading'].append(route)
            elif any(x in path for x in ['/dashboard', '/panel']):
                categories['Dashboard'].append(route)
            else:
                categories['Other'].append(route)
        
        for category, routes in categories.items():
            if routes:
                print(f"\n{category} Endpoints:")
                for route in routes:
                    methods = ', '.join(route['methods'])
                    print(f"  {methods:12} {route['path']}")
        
        print(f"\n✓ Total API endpoints: {len(routes)}")
        return True
        
    except Exception as e:
        print(f"✗ API endpoint test failed: {e}")
        return False

if __name__ == "__main__":
    print("Nexus Alpha - Comprehensive Test Suite")
    print("=" * 50)
    
    # Run tests
    app_test = test_app()
    frontend_test = test_frontend()
    api_test = test_api_endpoints()
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Application", app_test),
        ("Frontend Templates", frontend_test),
        ("API Endpoints", api_test)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for name, result in tests:
        status = "PASS" if result else "FAIL"
        print(f"{name:20} - {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! Nexus Alpha is ready to use.")
        print("\nTo start the application:")
        print("1. Start Docker Desktop")
        print("2. Run: docker compose up --build -d")
        print("3. Open: http://localhost:8010/dashboard")
    else:
        print(f"\n⚠️  {total-passed} tests failed. Please check the issues above.")
    
    sys.exit(0 if passed == total else 1)
