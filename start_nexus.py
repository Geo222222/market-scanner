#!/usr/bin/env python3
"""
Nexus Alpha Startup Script
Works without Docker Desktop
"""
import sys
import os
import subprocess
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'redis',
        'psycopg',
        'ccxt',
        'pandas'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"PASS - {package}")
        except ImportError:
            missing.append(package)
            print(f"FAIL - {package} - Missing")
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    return True

def start_redis():
    """Start Redis using Docker (if available)"""
    print("\nStarting Redis...")
    try:
        # Try to start Redis with Docker
        result = subprocess.run([
            'docker', 'run', '-d', '--name', 'nexus-redis', 
            '-p', '6379:6379', 'redis:7-alpine'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("PASS - Redis started with Docker")
            return True
        else:
            print("FAIL - Failed to start Redis with Docker")
            return False
    except FileNotFoundError:
        print("FAIL - Docker not available")
        return False

def start_postgres():
    """Start PostgreSQL using Docker (if available)"""
    print("\nStarting PostgreSQL...")
    try:
        # Try to start PostgreSQL with Docker
        result = subprocess.run([
            'docker', 'run', '-d', '--name', 'nexus-postgres',
            '-p', '5432:5432',
            '-e', 'POSTGRES_USER=nexus',
            '-e', 'POSTGRES_PASSWORD=nexus', 
            '-e', 'POSTGRES_DB=nexus',
            'postgres:16'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("PASS - PostgreSQL started with Docker")
            return True
        else:
            print("FAIL - Failed to start PostgreSQL with Docker")
            return False
    except FileNotFoundError:
        print("FAIL - Docker not available")
        return False

def start_nexus():
    """Start the Nexus Alpha application"""
    print("\nStarting Nexus Alpha...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = 'src'
    os.environ['NEXUS_REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['NEXUS_POSTGRES_URL'] = 'postgresql://nexus:nexus@localhost:5432/nexus'
    os.environ['NEXUS_TRADING_ENABLED'] = 'false'
    
    try:
        # Start the application
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 'app:app',
            '--host', '0.0.0.0', '--port', '8010', '--reload'
        ], cwd='src')
    except KeyboardInterrupt:
        print("\nShutting down Nexus Alpha...")
    except Exception as e:
        print(f"Error starting Nexus Alpha: {e}")

def main():
    """Main startup function"""
    print("Nexus Alpha - Local Startup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install missing dependencies first:")
        print("pip install -r requirements.txt")
        return
    
    # Try to start databases
    redis_ok = start_redis()
    postgres_ok = start_postgres()
    
    if not redis_ok or not postgres_ok:
        print("\nWARNING - Database services not available")
        print("The application will start with limited functionality")
        print("For full functionality, start Docker Desktop and run:")
        print("docker compose up --build -d")
    
    print("\nStarting Nexus Alpha...")
    print("Access the dashboard at: http://localhost:8010/dashboard")
    print("Press Ctrl+C to stop")
    
    # Start the application
    start_nexus()

if __name__ == "__main__":
    main()
