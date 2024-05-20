from libs import Redis
import asyncio
import websockets
import json
from collections import defaultdict
import logging

logging.basicConfig(level=logging.DEBUG)
clients = defaultdict(set)


class Server:
    MAXIMUM = 5

    def __init__(self, host, port, redis_host, redis_port, maximum):
        self.host = host
        self.port = port
        self.redis = Redis.RedisClient(
            redis_host,
            redis_port
        )
        self.MAXIMUM = maximum

    async def serve(self):
        await self.redis.connect()
        server = await websockets.serve(lambda ws, path: self.handle_client(ws, path), self.host, self.port)

        task = asyncio.create_task(server.wait_closed())
        task2 = asyncio.create_task(self.launch())

        await asyncio.gather(task, task2)

    async def handle_client(self, ws, path):
        clients[path].add(ws)
        try:
            async for message in ws:
                print(message)
                try:
                    message: dict = json.loads(message)
                    action = message.get('action')
                    if action == "add":
                        print(f"Action is add")
                        message.pop("action")
                        message["channel"] = path
                        await self.redis.enqueue(message)

                    if action == "complete":
                        complete = message.get("complete")
                        await self.redis.complete(complete)
                        self.MAXIMUM += 1
                    if action == "flush":
                        await self.redis.flush()
                except Exception as e:
                    print(e)
                    pass
            pass
        except websockets.ConnectionClosed:
            clients[path].remove(ws)
            pass

    async def launch(self):
        print("This should be executed")
        while True:
            print(f"Current Maximum is {self.MAXIMUM}")
            if self.MAXIMUM > 0:
                item = await self.redis.launch()
                if item:
                    channel = item.get('channel')
                    for client in clients[channel]:
                        await client.send(json.dumps(item))
                    self.MAXIMUM -= 1
            await asyncio.sleep(1)
        print("This should never be called")


if __name__ == "__main__":
    a = Server("localhost", 8023, "localhost", 6379, 5)
    asyncio.run(a.serve())
    pass
