from abc import ABC, abstractmethod


class MarketAdapter(ABC):
    @abstractmethod
    async def fetch_market(self, symbol: str) -> dict:
        ...

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
