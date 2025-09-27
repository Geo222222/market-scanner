# Market Scanner

Async FastAPI service that continuously scores perp markets, caches the latest snapshots in Redis, persists minute aggregates to Postgres, and surfaces ranked opportunities plus heuristic trade setups.

## Features
- CCXT adapter with retries, per-call timeouts, and a circuit breaker
- Deterministic metrics pipeline (liquidity, spreads, ATR%, momentum, slippage, carry) with Pydantic snapshots
- Profile-aware scoring presets (`scalp`, `swing`, `news`) and hard liquidity/cost filters
- Redis hot cache for fast reads and Postgres minute aggregates for audit/backfill
- Background scan loop that refreshes continuously without blocking HTTP
- `/rankings` with paging + filters, `/opportunities` heuristic playbook, and `/panel` lightweight admin view

## Requirements
- Python **3.11+** (needed for newer typing syntax such as `float | None`)
- Docker (optional) for Redis/Postgres when you want full persistence
- CCXT credentials if you plan to hit exchanges that require authentication

If you are on Windows and using the included Miniconda environment, prefer running commands with `C:\Users\epinn\miniconda3\python.exe` so the correct interpreter is used.

## Configuration
1. Copy the sample environment file and tweak to taste:
   ```bash
   cp .env.example .env
   ```
2. Key knobs:
   - `SCANNER_EXCHANGE`: CCXT exchange id (default `binanceusdm`)
   - `SCANNER_MIN_QVOL_USDT`, `SCANNER_MAX_SPREAD_BPS`: hard filters
   - `SCANNER_POSTGRES_URL`, `SCANNER_REDIS_URL`: connection strings (set only when the stores are available)

## Bring Everything Up (Docker Compose)
```bash
cp .env.example .env  # customise thresholds + URLs as needed
docker compose up --build -d
curl -s "http://localhost:8010/health"
# after the loop warms up
curl "http://localhost:8010/rankings?top=12&profile=scalp&min_qvol=50000000&max_spread_bps=5&notional=10000"
curl "http://localhost:8010/opportunities?profile=scalp&top=12&notional=10000"
```

## Local Development (without Docker)
```bash
pip install -r requirements.txt
C:\Users\epinn\miniconda3\python.exe -m uvicorn market_scanner.app:app --host 127.0.0.1 --port 8010 --app-dir src
# open http://127.0.0.1:8010/docs and http://127.0.0.1:8010/panel
```
- If Redis/Postgres are not running locally the service will log warnings but continue to serve rankings from the last successful cycle.
- You can point `SCANNER_REDIS_URL`/`SCANNER_POSTGRES_URL` to remote services when available.

### One-off Live Snapshot Check
When you just need to verify the scanner can pull fresh data without running the HTTP server:
```bash
C:\Users\epinn\miniconda3\python.exe collect_once.py
```
This prints the top-ranked symbols, key metrics, and the snapshot timestamp directly from a full CCXT scan.

## Tests
```bash
pytest
```
