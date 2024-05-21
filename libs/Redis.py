import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)
PENDING = 'pending_queue'


class RedisClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.redis = None

    async def connect(self):
        self.redis = redis.Redis(
            host=self.host, port=self.port, decode_responses=True)

    async def calculate_priority(self, owner, project):
        owner_count = await self.redis.scard(f"running:owner:{owner}")
        project_count = await self.redis.scard(f"running:project:{project}")
        return (1 / (owner_count + 1)) + (1 / (project_count + 1))

    async def enqueue(self, item):
        owner = item["owner"]
        project = item["project"]
        command = item["command"]
        build = item["build"]
        channel = item["channel"]
        item_id = f"{channel}/{project}/{build}/{command}"
        item_key = f"item:{item_id}"

        priority = await self.calculate_priority(owner, project)

        item["priority"] = priority
        for field, value in item.items():
            await self.redis.hset(item_key, field, value)
        await self.redis.zadd(PENDING, {item_key: priority})
        logger.info(f"Item({item_id}) is added")

    async def launch(self):
        item_keys = await self.redis.zrange(PENDING, 0, 0)
        if not item_keys:
            logger.warning("No items available in the pending queue")
            return None

        logger.info(f"Item should be launched here {item_keys}")

        item_key = item_keys[0]
        item_details = await self.redis.hgetall(item_key)

        await self.redis.zrem(PENDING, item_key)

        owner = item_details['owner']
        project = item_details['project']

        await self.redis.sadd(f"running:owner:{owner}", item_key)
        await self.redis.sadd(f"running:project:{project}", item_key)
        await self.redis.sadd('running_queue', item_key)

        item_details["id"] = item_key
        return item_details

    async def complete(self, item):
        logger.debug(f"Complete item from redis. Item is {item}")
        project = item["project"]
        command = item["command"]
        build = item["build"]
        channel = item["channel"]

        item_id = f"item:{channel}/{project}/{build}/{command}"

        logger.debug(f"Complete target id:{item_id}")
        item_details = await self.redis.hgetall(item_id)

        if not item_details:
            logger.error("Item not found in running queue")
            return None

        owner = item_details["owner"]
        project = item_details["project"]

        logger.debug(f"Complete target owner : {owner}")
        logger.debug(f"Complete target project : {project}")
        await self.redis.srem(f"running:owner:{owner}", item_id)
        await self.redis.srem(f"running:project:{project}", item_id)
        await self.redis.srem('running_queue', item_id)
        await self.redis.delete(item_id)

        logger.info(f"Complete item {item}")

    async def flush(self):
        await self.redis.flushdb()
