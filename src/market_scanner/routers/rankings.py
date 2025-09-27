from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_rankings():
    # Placeholder; in production, load from DB
    return {"rankings": []}

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
