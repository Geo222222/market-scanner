from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..engine.streaming import get_ranking_broadcast

router = APIRouter()


@router.websocket("/rankings")
async def stream_rankings(ws: WebSocket) -> None:
    await ws.accept()
    broadcaster = get_ranking_broadcast()
    try:
        async for frame in broadcaster.subscribe():
            await ws.send_text(frame.model_dump_json())
    except WebSocketDisconnect:
        return


async def _event_generator() -> AsyncIterator[str]:
    broadcaster = get_ranking_broadcast()
    async for frame in broadcaster.subscribe():
        payload = frame.model_dump(mode="json")
        yield f"data: {json.dumps(payload)}\n\n"


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    generator = _event_generator()

    async def event_stream():
        try:
            async for chunk in generator:
                if await request.is_disconnected():
                    break
                yield chunk
        finally:
            await generator.aclose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.websocket("/")
async def heartbeat(ws: WebSocket) -> None:
    await ws.accept()
    seq = 0
    try:
        while True:
            await ws.send_json({"type": "heartbeat", "seq": seq})
            seq += 1
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        return
