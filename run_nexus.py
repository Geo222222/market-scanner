#!/usr/bin/env python3
"""
Nexus Alpha - Direct Run Script
Fixes import issues and starts the application
"""
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables
os.environ['PYTHONPATH'] = 'src'
os.environ['NEXUS_REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['NEXUS_POSTGRES_URL'] = 'postgresql://nexus:nexus@localhost:5432/nexus'
os.environ['NEXUS_TRADING_ENABLED'] = 'false'
os.environ['NEXUS_EXCHANGE'] = 'htx'
os.environ['NEXUS_MIN_CONFIDENCE'] = '70.0'
os.environ['NEXUS_MAX_SPREAD_BPS'] = '8'

def main():
    """Start Nexus Alpha directly"""
    print("Nexus Alpha - Starting Application")
    print("=" * 40)
    print("Setting up environment...")
    print(f"Python path: {sys.path[0]}")
    print(f"Redis URL: {os.environ['NEXUS_REDIS_URL']}")
    print(f"PostgreSQL URL: {os.environ['NEXUS_POSTGRES_URL']}")
    print(f"Trading enabled: {os.environ['NEXUS_TRADING_ENABLED']}")
    print()
    
    try:
        # Import and start the app
        print("Importing application...")
        from app import app
        print("✓ Application imported successfully")
        
        print("\nStarting server...")
        print("Access the dashboard at: http://localhost:8010/dashboard")
        print("Press Ctrl+C to stop")
        print("=" * 40)
        
        # Start uvicorn
        import uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8010,
            reload=True,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you're in the project root directory")
        print("2. Check that all dependencies are installed: pip install -r requirements.txt")
        print("3. Verify the src/ directory structure")
        return 1
    except Exception as e:
        print(f"✗ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
