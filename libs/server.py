import asyncio
import json
import logging
from collections import defaultdict

import websockets
from libs import Redis

# Configure logging
logger = logging.getLogger(__name__)
clients = defaultdict(set)


class Server:
    def __init__(self, host, port, redis_host, redis_port, maximum):
        self.host = host
        self.port = port
        self.redis = Redis.RedisClient(redis_host, redis_port)
        self.MAXIMUM = maximum
        logger.debug("Server initialized with host %s, port %s, redis_host %s, redis_port %s, maximum %d",
                     host, port, redis_host, redis_port, maximum)

    async def serve(self):
        await self.redis.connect()
        self.CURRENT = await self.redis.redis.scard('running_queue')
        logger.warn(f"Existing running queue is {self.CURRENT}")

        server = await websockets.serve(self.handle_client, self.host, self.port)
        logger.info("WebSocket server started on %s:%s", self.host, self.port)

        task = asyncio.create_task(server.wait_closed())
        task2 = asyncio.create_task(self.launch())

        await asyncio.gather(task, task2)

    async def handle_client(self, ws, path):
        clients[path].add(ws)
        logger.info("Client connected: %s", path)
        try:
            async for message in ws:
                try:
                    message = json.loads(message)
                    logger.debug("Received message: %s", message)
                    action = message.get('action')

                    if action == "add":
                        message.pop("action")
                        message["channel"] = path
                        await self.redis.enqueue(message)
                        logger.info("Message enqueued: %s", message)

                    elif action == "complete":
                        message["channel"] = path
                        await self.redis.complete(message)
                        self.CURRENT -= 1
                        logger.info("Message completed: %s", message)

                    elif action == "flush":
                        await self.redis.flush()
                        logger.info("Redis flushed")
                except Exception as e:
                    logger.error("Error processing message: %s",
                                 e, exc_info=True)
        except websockets.ConnectionClosed:
            clients[path].remove(ws)
            logger.info("Client disconnected: %s", path)

    async def launch(self):
        while True:
            if self.CURRENT < self.MAXIMUM:
                item = await self.redis.launch()
                if item:
                    channel = item.get('channel')
                    logger.debug("Launching item: %s", item)
                    for client in clients[channel]:
                        await client.send(json.dumps(item))
                    self.CURRENT += 1
                    logger.info("Item launched and sent to clients: %s", item)
            else:
                logger.warning("Current running is too many")
            await asyncio.sleep(1)


if __name__ == "__main__":
    logger.basicConfig(level=logging.info)
    server = Server("localhost", 8023, "localhost", 6379, 5)
    asyncio.run(server.serve())
