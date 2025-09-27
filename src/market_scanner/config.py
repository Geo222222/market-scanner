from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Market Scanner"
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/scanner"
    alert_system_url: str = "http://alert-api:8000/events"
    symbols: list[str] = ["BTC/USDT:USDT", "ETH/USDT:USDT", "DOGE/USDT:USDT"]
    scan_interval_s: int = 10

    class Config:
        env_file = ".env"
        env_prefix = "SCANNER_"


settings = Settings()

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
