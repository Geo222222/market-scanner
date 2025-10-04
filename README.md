# Market Scanner

FastAPI service that ranks perpetual markets in real time, blending liquidity, cost, momentum, and manipulation risk into a single score. Snapshots are cached in Redis, aggregates land in Postgres, and the new /panel serves a trader-facing command center straight from the API.


## What's New
- Futuristic `/panel` dashboard served directly from FastAPI (Tailwind + Alpine, no build step).
- Auto-refreshing rankings table with manual refresh button and connection health chip.
- Spotlight quick search (type a symbol like `BTC/USDT:USDT`, hit Enter for instant drill-down).
- Slide-out Settings drawer that persists profile/top/notional tweaks, weight sliders, lists, and manipulation threshold to `localStorage`.
- Toast notifications for refresh success and API errors so polling keeps going even if `/rankings` returns 5xx.
- Theme toggle (Matrix Dark / Light) with glassmorphism styling.

## Core Platform Highlights
- **Risk-weighted scoring** - profile-aware presets (`scalp`, `swing`, `news`) blend liquidity, ATR%, momentum, spreads, slippage, and carry.
- **Manipulation detection** - heuristics and logistic layer surface spoofing, spoof-vacuum, wash-trade, and post-surge reversal risk.
- **Persistence & caching** - Redis for hot snapshots, Postgres for historical aggregates and replay.
- **Observability** - structured logs each scan plus optional Prometheus `/metrics` endpoint.
- **Extensible routing** - FastAPI routers compartmentalise health, rankings, opportunities, profiles, settings, watchlists, and streaming hooks.

## Requirements
- Python 3.11+
- Redis + Postgres (use Docker Compose recipe or point to existing instances)
- Optional exchange credentials if you need authenticated CCXT calls

## Configuration
1. Copy the sample env: `cp .env.example .env`
2. Tune keys as needed (all prefixed with `SCANNER_`):
   - `SCANNER_EXCHANGE` - exchange id (default `binanceusdm`)
   - `SCANNER_MIN_QVOL_USDT`, `SCANNER_MAX_SPREAD_BPS` - liquidity/cost guards
   - `SCANNER_REDIS_URL`, `SCANNER_POSTGRES_URL` - backing stores
   - `SCANNER_METRICS_ENABLED` - expose Prometheus endpoint

## Run with Docker Compose
```bash
docker compose up --build -d
```
Check services:
```bash
curl -s http://localhost:8010/health
curl -s "http://localhost:8010/rankings?top=12"
```
Open `http://localhost:8010/panel` in a browser to see the live dashboard.

Shut everything down when you are finished:
```bash
docker compose down
```

## Run Locally without Docker
```bash
pip install -r requirements.txt
uvicorn market_scanner.app:app --host 127.0.0.1 --port 8010 --app-dir src --reload
```
Redis/Postgres must be reachable via the URLs in `.env`.

## Panel Quick Tour
- **Live Table** - refreshes every 5s via HTTP polling; manual refresh triggers a toast on success.
- **Settings Drawer** - adjust profile/top/notional, weight sliders, whitelist/blacklist, and min manipulation risk; all saved to `localStorage`.
- **Spotlight** - enter a symbol to call `/opportunities?symbol=...`; cards show spread/slip/ATR/QVol/flags instantly.
- **Status Chip** - shows `Live` or `Error` plus "Updated Xs ago"; turns red when the latest fetch fails.
- **Error Handling** - failed polls raise a red toast and keep retrying; the UI stays rendered even if `/rankings` serves 503.
- **Theme Toggle** - switch between Matrix Dark and Light variants; choice persists across visits.

## Key Endpoints
- `GET /health` - readiness probe.
- `GET /rankings` - ranked markets (`top`, `profile`, `notional`, optional whitelist/blacklist/min_manip`).
- `GET /opportunities` - profile-specific ideas; Spotlight hits this for symbol cards.
- `GET /panel` - Command Center UI served from `routers/panel.py` (Tailwind + Alpine).
- `GET /stream/*` - streaming helpers ready for future websocket upgrades.
- `GET /metrics` - Prometheus scrape (enabled when `SCANNER_METRICS_ENABLED=true`).

## Tests
```bash
pytest -q
```

## Roadmap
- Swap polling for `/stream/rankings` WebSocket push once upstream stability is proven.
- Persist UI settings server-side and sync watchlists across devices.
- Add contextual screenshots/gifs to `docs/` and the README once design stabilises.
