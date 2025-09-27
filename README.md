# Market Scanner (Service B)

Async multi-symbol scanner that ranks opportunities and can post alerts to the Alert System service.

## Endpoints
- `GET /health`
- `GET /symbols`
- `GET /rankings`
- `GET /opportunities`
- `WS /stream`

## Quickstart (Docker)

```bash
cd market-scanner
cp .env.example .env
docker compose up --build -d
curl -s localhost:8010/health | jq
# enable CCXT (HTX) live data
# edit .env -> SCANNER_USE_CCXT=1 and set HTX_KEY/HTX_SECRET if needed, then restart
```

## Dev
- Python 3.11+
- `pip install -r requirements.txt`
- `uvicorn market_scanner.app:app --reload --port 8010`

> Note: Uses a mock adapter and in-memory loop for the demo.

<!-- ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark -->
<!-- Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME. -->
<!-- ONNYX · ONNX · DJM · DJ · ME · Jamaica -->
