from fastapi import APIRouter
from ..config import settings

router = APIRouter()


@router.get("/")
async def list_symbols():
    return [{"name": s, "active": True} for s in settings.symbols]

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
