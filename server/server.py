import asyncio
import json
import os
import signal

import websockets

from handlers import addNewPerson, processContent, replyScore, requestClient

MEETS = {}

async def handler(websocket, path):
    async for message in websocket:
        msg = json.loads(message)
        if msg["event"] == "init":
            await addNewPerson(websocket, msg, MEETS)

        elif msg["event"] == "content":
            await processContent(msg["meetCode"], MEETS, msg["data"])

        elif msg["event"] == "request":
            await requestClient(msg["meetCode"], MEETS, "frames")

        elif msg["event"] == "reply":
            await replyScore(websocket, msg, MEETS)


async def main():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)

    port = int(os.environ.get("PORT", "8001"))
    async with websockets.serve(handler, "", port):
        await stop

asyncio.run(main())
