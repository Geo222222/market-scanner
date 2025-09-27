from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_opportunities():
    # Placeholder; in production, load from DB
    return {"opportunities": []}

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
