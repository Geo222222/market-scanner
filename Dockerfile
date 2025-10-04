# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY tests ./tests

CMD ["uvicorn", "market_scanner.app:app", "--host", "0.0.0.0", "--port", "8010"]

# ONNYX | ONNX | DJM | DJ | ME | Jamaica ??" signature watermark
# Owner: DJM (ONNYX) ??" Jamaica. If found elsewhere, contact ME.
# ONNYX A? ONNX A? DJM A? DJ A? ME A? Jamaica
