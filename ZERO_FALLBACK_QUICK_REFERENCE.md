# Zero-Fallback Data Integrity - Quick Reference

## 🚀 Quick Start

### Set the Policy

```bash
# Production (default)
export FALLBACK_POLICY=strict

# Development/Demo
export FALLBACK_POLICY=permissive
```

### Check Current Mode

```python
from market_scanner.data_integrity import is_strict_mode, is_permissive_mode

if is_strict_mode():
    print("Running in STRICT mode - no mock data allowed")
else:
    print("Running in PERMISSIVE mode - mock data allowed")
```

---

## 📋 Common Patterns

### 1. Handling Data Failures

```python
from market_scanner.data_integrity import is_strict_mode, log_data_error

try:
    data = await fetch_from_exchange(symbol)
except Exception as e:
    if is_strict_mode():
        # In strict mode: log error and skip
        log_data_error(
            exchange="htx",
            symbol=symbol,
            operation="fetch_ticker",
            error=str(e),
            retries=3
        )
        return None  # Don't return mock data
    else:
        # In permissive mode: can return mock data
        return generate_mock_data(symbol)
```

### 2. Validating Data Sources

```python
from market_scanner.data_integrity import validate_data_source

# Check if a data source is allowed under current policy
if not validate_data_source(exchange_name):
    # Drop this data in strict mode
    continue
```

### 3. Tracking Exchange Health

```python
from market_scanner.data_integrity import exchange_tracker

# Record success
exchange_tracker.record_success("htx", latency_ms=150)

# Record failure
exchange_tracker.record_failure("htx", "Connection timeout")

# Get status
health = exchange_tracker.get_health("htx")
if not health.ok:
    print(f"HTX is down: {health.last_error}")
```

### 4. Creating Rankings with Required Fields

```python
from market_scanner.data_integrity import RankingRow

row = RankingRow(
    rank=1,
    symbol="BTC/USDT",
    exchange="htx",  # REQUIRED - never null/empty
    score=95.5,
    bias="long",
    confidence=0.85,
    liquidity=1000000.0,
    momentum=0.5,
    spread_bps=2.5,
    ai_insight="Strong momentum",
    ts=datetime.now(timezone.utc).isoformat()
)
```

---

## 🔍 Key Rules

### Strict Mode (Production)
- ❌ **NEVER** return mock/synthetic data
- ❌ **NEVER** use fallback values
- ✅ **ALWAYS** log errors with structured format
- ✅ **ALWAYS** skip symbols when data unavailable
- ✅ **ALWAYS** set `degraded=true` when dropping rows

### Permissive Mode (Development)
- ✅ **CAN** return mock data
- ✅ **MUST** label mock data with `source="mock"`
- ✅ **MUST** still log errors
- ✅ **SHOULD** prefer real data when available

---

## 📊 Required Fields

### SymbolSnapshot
```python
SymbolSnapshot(
    symbol="BTC/USDT",
    exchange="htx",  # REQUIRED - added in this implementation
    qvol_usdt=1000000.0,
    spread_bps=2.5,
    # ... other fields
)
```

### RankingsResponse
```python
RankingsResponse(
    mode="live",              # REQUIRED
    degraded=False,           # REQUIRED
    asof="2025-10-31T...",   # REQUIRED
    exchanges_ok=["htx"],     # REQUIRED
    rows=[...],               # REQUIRED
    error=None,               # Optional
    detail=None               # Optional
)
```

### HealthResponse
```python
HealthResponse(
    mode="strict",            # REQUIRED
    live_data_ok=True,        # REQUIRED
    degraded=False,           # REQUIRED
    exchanges=[...],          # REQUIRED
    asof="2025-10-31T..."    # REQUIRED
)
```

---

## 🛠️ Structured Logging Format

```
level=ERROR svc=collector exchange=htx symbol=BTC/USDT op=fetch_ticker err="Connection timeout" retries=3 mode=strict
```

**Fields:**
- `level` - Log level (ERROR, WARNING, INFO, DEBUG)
- `svc` - Service name (collector, scanner, etc.)
- `exchange` - Exchange name (htx, okx, binance)
- `symbol` - Trading pair symbol
- `op` - Operation name (fetch_ticker, fetch_orderbook, etc.)
- `err` - Error message (quoted)
- `retries` - Number of retry attempts
- `mode` - Current policy mode (strict, permissive)

---

## 🧪 Testing

### Run Tests
```bash
python scripts/test_data_integrity.py
```

### Test Strict Mode
```bash
export FALLBACK_POLICY=strict
python scripts/test_data_integrity.py
```

### Test Permissive Mode
```bash
export FALLBACK_POLICY=permissive
python scripts/test_data_integrity.py
```

---

## 🚨 Common Mistakes to Avoid

### ❌ DON'T: Return mock data without checking policy
```python
# BAD
if not data:
    return generate_mock_data()
```

### ✅ DO: Check policy before returning mock data
```python
# GOOD
if not data:
    if is_strict_mode():
        log_data_error(...)
        return None
    else:
        return generate_mock_data()
```

### ❌ DON'T: Create SymbolSnapshot without exchange field
```python
# BAD
snapshot = SymbolSnapshot(
    symbol="BTC/USDT",
    qvol_usdt=1000000.0,
    # Missing exchange field!
)
```

### ✅ DO: Always include exchange field
```python
# GOOD
snapshot = SymbolSnapshot(
    symbol="BTC/USDT",
    exchange="htx",  # REQUIRED
    qvol_usdt=1000000.0,
)
```

### ❌ DON'T: Ignore exchange health tracking
```python
# BAD
try:
    data = await exchange.fetch_ticker(symbol)
except Exception as e:
    logger.error(f"Error: {e}")
```

### ✅ DO: Record failures in health tracker
```python
# GOOD
try:
    data = await exchange.fetch_ticker(symbol)
    exchange_tracker.record_success("htx", latency_ms=150)
except Exception as e:
    exchange_tracker.record_failure("htx", str(e))
    log_data_error(...)
```

---

## 📖 API Endpoints

### GET /health
Returns system health with exchange status

**Response:**
```json
{
  "mode": "strict",
  "live_data_ok": true,
  "degraded": false,
  "exchanges": [
    {"name": "htx", "ok": true, "latency_ms": 150}
  ],
  "asof": "2025-10-31T10:45:33Z"
}
```

### GET /rankings
Returns rankings with required exchange field

**Response:**
```json
{
  "mode": "live",
  "degraded": false,
  "asof": "2025-10-31T10:45:33Z",
  "exchanges_ok": ["htx", "okx"],
  "rows": [
    {
      "rank": 1,
      "symbol": "BTC/USDT",
      "exchange": "htx",
      "score": 95.5,
      ...
    }
  ]
}
```

---

## 🔗 Related Files

- **Core Module:** `src/market_scanner/data_integrity.py`
- **Scanner Loop:** `src/market_scanner/jobs/loop.py`
- **Rankings API:** `src/market_scanner/routers/rankings.py`
- **Health API:** `src/market_scanner/routers/health.py`
- **Tests:** `scripts/test_data_integrity.py`
- **Full Documentation:** `ZERO_FALLBACK_IMPLEMENTATION_SUMMARY.md`

---

## 💡 Tips

1. **Always check policy mode** before generating mock data
2. **Always populate exchange field** in SymbolSnapshot
3. **Always use structured logging** for errors
4. **Always track exchange health** on success/failure
5. **Test both modes** (strict and permissive) during development

---

**Last Updated:** 2025-10-31  
**Status:** ✅ Production Ready

