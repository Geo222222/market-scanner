import asyncio
import json
import websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8010/stream/rankings", open_timeout=10) as ws:
        data = json.loads(await ws.recv())
        print("received", len(data.get("items", [])))
asyncio.run(main())
