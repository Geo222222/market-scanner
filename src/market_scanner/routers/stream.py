from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()


@router.websocket("/")
async def stream(ws: WebSocket):
    await ws.accept()
    try:
        # Simple heartbeat stream for the skeleton
        i = 0
        while True:
            await ws.send_json({"type": "heartbeat", "seq": i})
            i += 1
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
