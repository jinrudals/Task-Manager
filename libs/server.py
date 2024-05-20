import asyncio
import json
import logging
from collections import defaultdict

import websockets
from libs import Redis

# Configure logging
clients = defaultdict(set)


class Server:
    def __init__(self, host, port, redis_host, redis_port, maximum):
        self.host = host
        self.port = port
        self.redis = Redis.RedisClient(redis_host, redis_port)
        self.MAXIMUM = maximum
        logging.debug("Server initialized with host %s, port %s, redis_host %s, redis_port %s, maximum %d",
                      host, port, redis_host, redis_port, maximum)

    async def serve(self):
        await self.redis.connect()
        server = await websockets.serve(self.handle_client, self.host, self.port)
        logging.info("WebSocket server started on %s:%s", self.host, self.port)

        task = asyncio.create_task(server.wait_closed())
        task2 = asyncio.create_task(self.launch())

        await asyncio.gather(task, task2)

    async def handle_client(self, ws, path):
        clients[path].add(ws)
        logging.info("Client connected: %s", path)
        try:
            async for message in ws:
                try:
                    message = json.loads(message)
                    logging.debug("Received message: %s", message)
                    action = message.get('action')

                    if action == "add":
                        message.pop("action")
                        message["channel"] = path
                        await self.redis.enqueue(message)
                        logging.info("Message enqueued: %s", message)

                    elif action == "complete":
                        message["channel"] = path
                        await self.redis.complete(message)
                        self.MAXIMUM += 1
                        logging.info("Message completed: %s", message)

                    elif action == "flush":
                        await self.redis.flush()
                        logging.info("Redis flushed")
                except Exception as e:
                    logging.error("Error processing message: %s",
                                  e, exc_info=True)
        except websockets.ConnectionClosed:
            clients[path].remove(ws)
            logging.info("Client disconnected: %s", path)

    async def launch(self):
        while True:
            if self.MAXIMUM > 0:
                item = await self.redis.launch()
                if item:
                    channel = item.get('channel')
                    logging.debug("Launching item: %s", item)
                    for client in clients[channel]:
                        await client.send(json.dumps(item))
                    self.MAXIMUM -= 1
                    logging.info("Item launched and sent to clients: %s", item)
            await asyncio.sleep(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.info)
    server = Server("localhost", 8023, "localhost", 6379, 5)
    asyncio.run(server.serve())
