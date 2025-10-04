# Advance Market Scanner (HTX USDT-M)

Async FastAPI service that continuously ranks HTX USDT-margined perpetual swaps by risk-adjusted opportunity. The scanner ingests live market data via CCXT, computes liquidity/cost/volatility/momentum metrics, estimates manipulation risk, caches hot snapshots in Redis, and persists minute aggregates and rankings into Postgres.


## Core Highlights
- **Risk-weighted scoring** - profile-aware presets (`scalp`, `swing`, `news`) combine liquidity, ATR%, momentum, spread, slippage, and carry inputs.
- **Cross-sectional intelligence** - cycle-level z-scores (liquidity, momentum, volatility, microstructure) highlight the most tradeable contracts using order-book resilience concepts from Hasbrouck (2007) and Easley & O'Hara (2012).
- **Manipulation detection** - heuristics plus a refreshed logistic layer surface spoofing reversals, liquidity vacuums, exhausted spikes, funding/OI divergences, and post-surge reversals with `manip_score` (0-100) + `manip_flags`.
- **HTX linear swaps only** - auto-discovers active USDT-M perps with concurrency limits and a CCXT circuit breaker to guard the exchange.
- **Persistence & caching** - Redis serves the freshest snapshots while Postgres stores minute aggregates and ranking history for replay and audits.
- **Observability** - JSON structured logs per cycle plus a Prometheus `/metrics` endpoint for latency, cache hits, and error counters.
- **Realtime operator console** - `/panel` streams rankings via WebSocket/SSE, offers Spotlight search, a manipulation-aware drawer, and live latency/health metrics.
- **Alerts & signal bus** - configurable Redis pub/sub channel (`scanner.signals`) with rule-based triggers and optional webhook fan-out.

## Requirements
- Python **3.11+** (PEP 604 typing in use)
- Redis & Postgres (Docker Compose recipe included)
- Optional: HTX API credentials if you prefer authenticated calls (not required for public perp data)
- Recommended on Windows: use the bundled Miniconda env (`C:\Users\epinn\miniconda3\python.exe`)

## Quick Start (Docker Compose)

1. Start Docker Desktop (or another Docker Engine) and make sure it has outbound network access.
2. Copy `.env.example` to `.env` and tweak any knobs you need:
   - `SCANNER_SYMBOLS` defaults to a curated list of liquid HTX perps so the first run finishes quickly. Remove the value to scan everything once you are comfortable.
   - `SCANNER_ADAPTER_TIMEOUT_SEC` controls how long we wait on HTX responses. The exchange is slow; 120s is a pragmatic starting point.
   - `SCANNER_CA_BUNDLE_PATH` / `REQUESTS_CA_BUNDLE` let you point at a corporate CA bundle if outbound TLS is intercepted.
3. Build and start the stack:

```bash
docker compose up --build -d
```

4. Tail the API logs until you see a `scan_cycle` message. The first pass can take 3-4 minutes with the default allow list while HTX data warms up.

```bash
docker compose logs -f api
```

5. Validate each service once the first cycle completes:

```bash
curl -s http://localhost:8010/health
curl -s "http://localhost:8010/rankings?top=5"
# open the operator panel in a browser
start http://localhost:8010/panel
# optional sanity checks
docker compose exec postgres pg_isready -U scanner -d scanner
docker compose exec redis redis-cli ping
```

6. When you are done, tear everything down with `docker compose down`.

**Heads up:** rankings and snapshots are cached in Redis for ~90 seconds. If you query the API outside that window you will get a 503 until the next scan finishes (watch the logs to confirm progress).

## Realtime Operator Console
- `/panel` opens a streaming table fed by `WS /stream/rankings` with an automatic SSE fallback at `/stream/events` for environments that block websockets.
- Spotlight (`Ctrl+K`) queries `/symbol/{id}/inspect?mode=card` so you can jump to any contract without waiting for the batch loop.
- Clicking a row loads `/symbol/{id}/inspect`, rendering sparklines, trade/microstructure readouts, execution metrics, and manipulation diagnostics.
- The settings drawer persists sliders to `/settings` & `/watchlists`, hot-applies presets via `/profiles/apply`, and reflects the cached profile state.
- The "System Health" widget polls `/healthz/details` to surface per-symbol latency, adaptive backoff windows, and CCXT circuit-breaker status.
- Alerts triggered by ranking deltas or manipulation hits fan out through the Redis channel defined by `SCANNER_SIGNAL_CHANNEL`; optional webhooks are controlled via `SCANNER_ALERT_WEBHOOK_URL`.

## Local Development (without Docker)

1. Copy `.env.example` to `.env` and adjust the same knobs described above (symbol allow list, timeouts, CA bundle).
2. Make sure you have Redis and Postgres available locally. The easiest path is to reuse the Docker services (`docker compose up redis postgres`) or point `SCANNER_REDIS_URL` / `SCANNER_POSTGRES_URL` at existing instances.
3. Install the dependencies and start Uvicorn:

```bash
pip install -r requirements.txt
C:\Users\epinn\miniconda3\python.exe -m uvicorn market_scanner.app:app --host 127.0.0.1 --port 8010 --app-dir src --reload
```

4. Wait for the background scan to complete (watch the terminal for the `scan_cycle` log) and hit `http://127.0.0.1:8010/rankings?top=5` or open `/panel` in a browser.

For a quick, one-off sanity check without the API you can run:

```bash
C:\Users\epinn\miniconda3\python.exe collect_once.py
```

That prints the top-ranked symbols, key metrics, manipulation score, and snapshot timestamp using the same settings as the service.

## Make Targets
| Command | Description |
|---------|-------------|
| `make fmt` | Format `src/` and `tests/` with Ruff. |
| `make lint` | Run `ruff check` (warnings only, exit code ignored in CI). |
| `make test` | Execute the pytest suite (`pytest -q`). |
| `make up` | `docker compose up -d --build` for the full stack. |
| `make down` | `docker compose down` to stop containers. |
| `make seed` | Run `collect_once.py` to warm Redis/Postgres snapshots. |

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


## Intelligence Metrics

| Field | Meaning |
|-------|---------|
| `depth_to_volume_ratio` | Top five level book depth divided by the latest bar quote volume (liquidity resilience per Kyle depth models). |
| `liquidity_edge` | Cross-sectional liquidity z-score; positive values indicate deeper, tighter markets than the cycle median. |
| `momentum_edge` | Cross-sectional momentum z-score built from 1m/15m returns. |
| `volatility_edge` | Cross-sectional realized volatility z-score focusing on volatility clustering. |
| `microstructure_edge` | Inverted microstructure penalty capturing orderly vs noisy order flow (derived from order-flow imbalance, volume shocks, and velocity). |
| `anomaly_residual` | Residual anomaly pressure after normalising pump-and-dump features; positive implies elevated manipulation risk relative to peers. |

These factors feed the scoring presets and manipulation detector. Liquidity and microstructure edges lean on order-book resilience research (Hasbrouck, 2007) while anomaly residuals extend the flow imbalance heuristics from Easley & O'Hara (2012) and modern pump-and-dump studies. Each scan cycle recomputes the baseline so signals stay adaptive intraday.

## Endpoints
- `GET /health` - readiness ping.
- `GET /healthz/details` - expanded telemetry covering scan latency, breaker state, and stale symbols.
- `GET /rankings` - pageable, filterable rankings. Supports `top`, `profile`, `min_qvol`, `max_spread_bps`, `notional`, `include_funding`, `include_basis`, `include_carry`, `max_manip_score`, and `exclude_flags` query params.
- `GET /opportunities` - top-N idea list with side bias, ATR-derived stops/targets, and confidence penalised by manipulation risk.
- `GET /panel` - realtime scalper console streaming rankings, drill-downs, and health telemetry.
- `WS /stream/rankings` - primary WebSocket feed for ranking frames (JSON payloads).
- `GET /stream/events` - Server-Sent Events fallback emitting the same ranking frames.
- `WS /stream` - lightweight heartbeat to help uptime monitors keep the connection warm.
- `GET /symbol/{symbol}/inspect` - detailed microstructure, execution metrics, and order book snapshots for a single contract.
- `GET|POST /settings` - persist operator profile weights, manipulation threshold, and notional overrides.
- `GET|POST /watchlists` - create or update saved watchlists that drive panel filters.
- `GET /profiles` & `POST /profiles/apply` - manage and hot-apply scoring presets without restarting the service.
- `GET /metrics` - Prometheus metrics (enabled when `SCANNER_METRICS_ENABLED=true`).

## Manipulation Score

The manipulation layer now consumes the new microstructure diagnostics (volume z-score, volatility regime, pump-dump score) alongside depth/funding heuristics. High post-surge reversals or thin depth following outsized volume flag `post_surge_reversal` and `wash_trade_volume` so risky books are demoted before serving to clients.

Each symbol snapshot carries:
- `manip_score` (0-100): higher means more manipulation risk and is subtracted from the base score.
- `manip_flags`: textual reasons (e.g., `spoofing_depth_imbalance`, `liquidity_vacuum`, `scam_wick`, `oi_price_divergence`).

Flags come from a hybrid approach:
1. **Rules** - large top-of-book imbalances, shallow books vs notional, extreme wick/ATR ratios, funding & OI divergences.
2. **Lightweight logistic model** - engineered features (depth skew, wall ratio, wick ratio, OI delta, funding magnitude) convert to an additional probability-style score.

`/rankings` can filter by `exclude_flags` or `max_manip_score`. `/opportunities` folds the manipulation penalty into confidence so high-risk names get deprioritized.

## Microstructure Signals

The scanner now persists additional microstructure metrics with every snapshot:

- `volume_zscore`: rolling z-score of the latest bar volume vs. a 60-bar baseline to spotlight liquidity surges.
- `order_flow_imbalance`: normalized top-of-book imbalance, highlighting dominant resting interest (a proxy for latent pressure).
- `volatility_regime`: short/long realized volatility ratio, exposing clustering and regime shifts.
- `price_velocity`: short-horizon price velocity to boost or penalise trending vs. mean-reverting books.
- `anomaly_score`: composite pump-and-dump / wash-trading detector that mixes volume spikes, velocity reversals, and volatility jumps.

These hook into both ranking weights and manipulation penalties. Heuristics draw on stylised facts from market microstructure literature (Hasbrouck 2007; Cartea, Jaimungal & Penalva 2015) and enforcement case studies from the CFTC/ESMA.

## Observability
- Logs: each scan emits a JSON payload with cycle duration, symbols scanned, ranked count, and any flagged symbols + features.
- Metrics: `/metrics` exposes cycle duration histogram, CCXT call latency histogram, cache hit/miss counters, and cumulative error counts.

## Tests
```bash
pytest
```
The suite covers metric helpers, scoring monotonicity, manipulation heuristics, and a smoke-level API test with mocked rankings.
