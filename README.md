# 📊 Market Scanner

An **async FastAPI service** that continuously scans and scores perpetual futures (perp) markets.  
It calculates **liquidity, spreads, volatility, momentum, and slippage**, caches fresh data in **Redis**, stores historical aggregates in **Postgres**, and exposes **ranked trading opportunities** via HTTP endpoints and a lightweight web panel.

---

## 🚀 Features

- ⚡ **Continuous scanning loop** — runs in the background without blocking HTTP requests.
- 🌐 **Exchange support via [CCXT](https://github.com/ccxt/ccxt)** with:
  - Retries & timeouts
  - Circuit breaker for unstable exchanges
- 📈 **Deterministic metrics pipeline**:
  - Liquidity (quote volume)
  - Spreads (bps)
  - ATR% (volatility)
  - Momentum
  - Slippage estimate (based on your notional size)
  - Carry metrics
- 🎯 **Profile-aware scoring presets**: `scalp`, `swing`, `news`
- 🛡️ **Hard filters** for minimum liquidity & maximum spread
- ⚙️ **Storage**:
  - **Redis** — hot cache for ultra-fast reads
  - **Postgres** — minute-level aggregates for history/audit/backfill
- 🖥️ **HTTP API & Admin Panel**:
  - `/rankings` — top ranked symbols
  - `/opportunities` — heuristic playbook
  - `/panel` — minimal admin view
  - `/docs` — auto-generated API docs (Swagger UI)

---

## 📦 Requirements

- **Python 3.11+** (new typing features used)
- **Conda** (recommended) or any other virtual env tool
- **Docker** (optional) — to easily run Redis & Postgres locally
- **CCXT API keys** (only if you need authenticated endpoints)

> 💡 On Windows, if using Miniconda, commands may need to be prefixed with the full interpreter path  
> e.g. `C:\Users\YourName\miniconda3\python.exe`.

---

## ⚙️ Quick Start (Local Development)

### 1️⃣ Clone the repository

```bash
git clone https://github.com/Geo222222/market-scanner.git
cd market-scanner
