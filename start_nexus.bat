@echo off
echo Starting Nexus Alpha...
echo.

REM Set Python path
set PYTHONPATH=src

REM Set environment variables
set NEXUS_REDIS_URL=redis://localhost:6379/0
set NEXUS_POSTGRES_URL=postgresql://nexus:nexus@localhost:5432/nexus
set NEXUS_TRADING_ENABLED=false

REM Start the application
cd src
python -m uvicorn app:app --host 0.0.0.0 --port 8010 --reload

pause
