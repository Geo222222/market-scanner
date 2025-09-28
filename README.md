# Advance Market Scanner (HTX USDT-M)

Async FastAPI service that continuously ranks HTX USDT-margined perpetual swaps by risk-adjusted opportunity. The scanner ingests live market data via CCXT, computes liquidity/cost/volatility/momentum metrics, estimates manipulation risk, caches hot snapshots in Redis, and persists minute aggregates and rankings into Postgres.

## Core Highlights
- **Risk-weighted scoring** – profile-aware presets (`scalp`, `swing`, `news`) combine liquidity, ATR%, momentum, spread, and slippage with configurable carry inputs.
- **Manipulation detection** – heuristics + lightweight logistic model flag spoofing walls, liquidity vacuums, scam wicks, and funding/OI divergences. Each symbol carries a manip_score (0–100) and manip_flags list.
- **HTX linear swaps only** – auto-discovers active USDT-M perps, throttled by concurrency limits and a circuit breaker around CCXT.
- **Persistence & caching** – Redis serves the most recent rankings instantly while Postgres stores 1-minute aggregates and historical rankings for forensic replay.
- **Observability** – JSON structured logs per cycle plus a Prometheus `/metrics` endpoint (cycle duration, CCXT latency, cache hit ratio, error counters).
- **Operator panel** – minimal `/panel` view with live Top-N table, manipulation badges, and refresh-on-demand.

## Requirements
- Python **3.11+** (PEP 604 typing in use)
- Redis & Postgres (Docker Compose recipe included)
- Optional: HTX API credentials if you prefer authenticated calls (not required for public perp data)
- Recommended on Windows: use the bundled Miniconda env (`C:\Users\epinn\miniconda3\python.exe`)

## Quick Start (Docker Compose)
```bash
cp .env.example .env            # adjust thresholds, URLs, credentials if needed
docker compose up --build -d    # launches app + Redis + Postgres
curl -s http://localhost:8010/health
# after one or two cycles (~15s interval)
curl "http://localhost:8010/rankings?top=12&profile=scalp&min_qvol=20000000&max_spread_bps=8&notional=5000"
curl "http://localhost:8010/opportunities?profile=scalp&top=8&notional=5000"
open http://localhost:8010/panel
```

## Local Development (without Docker)
```bash
pip install -r requirements.txt
C:\Users\epinn\miniconda3\python.exe -m uvicorn market_scanner.app:app --host 127.0.0.1 --port 8010 --app-dir src
```
- Redis/Postgres are optional; the service logs warnings and keeps serving last-good results if either store is unavailable.
- For an ad-hoc sanity check without running the API:
  ```bash
  C:\Users\epinn\miniconda3\python.exe collect_once.py
  ```
  This prints the top-ranked symbols, key metrics, manipulation score, and snapshot timestamp.

## Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `SCANNER_EXCHANGE` | `htx` | CCXT exchange id. |
| `SCANNER_MIN_QVOL_USDT` | `20000000` | Reject symbols with lower 24h quote volume. |
| `SCANNER_MAX_SPREAD_BPS` | `8` | Reject symbols whose spread exceeds this value. |
| `SCANNER_NOTIONAL_TEST` | `5000` | Notional used for slippage estimation. |
| `SCANNER_PROFILE_DEFAULT` | `scalp` | Default scoring profile for background loop. |
| `SCANNER_INCLUDE_CARRY` | `true` | Include funding/basis carry in scoring. |
| `SCANNER_SCAN_INTERVAL_SEC` | `15` | Delay between scan cycles. |
| `SCANNER_SCAN_CONCURRENCY` | `12` | Maximum concurrent CCXT calls. |
| `SCANNER_SCAN_TOP_BY_QVOL` | `60` | Universe size after quote-volume sorting. |
| `SCANNER_REDIS_URL` | `redis://redis:6379/0` | Redis connection string. |
| `SCANNER_POSTGRES_URL` | `postgresql+psycopg://scanner:scanner@postgres:5432/scanner` | Postgres URL (psycopg driver). |
| `SCANNER_METRICS_ENABLED` | `true` | Toggles the `/metrics` endpoint and Prometheus instrumentation. |

All settings can be overridden via environment variables or `.env` (see `.env.example`).

## Endpoints
- `GET /health` – readiness ping.
- `GET /rankings` – pageable, filterable rankings. Supports query params: `top`, `profile`, `min_qvol`, `max_spread_bps`, `notional`, `include_funding`, `include_basis`, `include_carry`, `max_manip_score`, `exclude_flags`.
- `GET /opportunities` – top-N idea list with side bias, ATR-derived stops/targets, confidence (penalised by manipulation risk).
- `GET /panel` – lightweight HTML view of the latest Top-N with flag badges.
- `GET /metrics` – Prometheus metrics (enabled when `SCANNER_METRICS_ENABLED=true`).
- `WS /stream` – heartbeat placeholder.

## Manipulation Score
Each symbol snapshot carries:
- `manip_score` (0–100): higher means more manipulation risk and is subtracted from the base score.
- `manip_flags`: textual reasons (e.g., `spoofing_depth_imbalance`, `liquidity_vacuum`, `scam_wick`, `oi_price_divergence`).

Flags come from a hybrid approach:
1. **Rules** – large top-of-book imbalances, shallow books vs notional, extreme wick/ATR ratios, funding & OI divergences.
2. **Lightweight logistic model** – engineered features (depth skew, wall ratio, wick ratio, OI delta, funding magnitude) convert to an additional probability-style score.

`/rankings` can filter by `exclude_flags` or `max_manip_score`. `/opportunities` folds the manipulation penalty into confidence so high-risk names get deprioritized.

## Observability
- Logs: each scan emits a JSON payload with cycle duration, symbols scanned, ranked count, and any flagged symbols + features.
- Metrics: `/metrics` exposes cycle duration histogram, CCXT call latency histogram, cache hit/miss counters, and cumulative error counts.

## Tests
```bash
pytest
```
The suite covers metric helpers, scoring monotonicity, manipulation heuristics, and a smoke-level API test with mocked rankings.
