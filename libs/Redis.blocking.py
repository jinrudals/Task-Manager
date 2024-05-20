import redis
import logging

logger = logging.getLogger(__name__)
PENDING = 'pending_queue'


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Redis(redis.Redis):

    def __init__(self, host, port) -> None:
        super().__init__(host=host, port=port, db=0)
        self.flush()

    def calculate_priority(self, owner, project):
        owner = self.scard(f"running:owner:{owner}")
        project = self.scard(f"running:project:{project}")

        return (1 / (owner + 1)) + (1 / (project + 1))

    def enque(self, item):
        owner = item["owner"]
        project = item["project"]

        item_id = self.incr('item_id')
        item_key = f"item:{item_id}"

        priority = self.calculate_priority(owner, project)

        item["priority"] = priority
        self.hmset(item_key, item)
        # self.hset(item_key, mapping=item)
        self.zadd(PENDING, {item_key: priority})
        logger.info(f"Item({item_id}) is added")

    def launch(self):
        item_keys = self.zrange(PENDING, 0, 0)
        if not item_keys:
            logger.warn("No items available in the pending queue")
            return None

        item_key = item_keys[0]
        item_details = self.hgetall(item_key)

        self.zrem(PENDING, item_key)

        owner = item_details[b'owner'].decode("utf-8")
        project = item_details[b'project'].decode('utf-8')

        self.sadd(f"running:owner:{owner}", item_key)
        self.sadd(f"running:project:{project}", item_key)
        self.sadd('running_queue', item_key)

        output = {k.decode('utf-8'): v.decode('utf-8')
                  for k, v in item_details.items()}
        output["id"] = item_key.decode("utf-8")
        return output

    def complete(self, item):
        item_details = self.hgetall(item)

        if not item_details:
            logger.error("Item not found in running queue")
            return None

        owner = item_details[b"owner"].decode("utf-8")
        project = item_details[b"project"].decode("utf-8")

        self.srem(f"running:owner:{owner}", item)
        self.srem(f"running:owner:{project}", item)

        self.srem('running_queue', item)

        self.delete(item)

        logger.info(f"Complete item {item}")

    def flush(self):
        self.flushdb()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    redis_queue = Redis(host='localhost', port=6379)

    # Add items to the queue
    redis_queue.enque(
        {'owner': 'owner1', 'project': 'projectA', 'timeout': 10})
    redis_queue.enque({'owner': 'owner2', 'project': 'projectA', 'timeout': 5})
    redis_queue.enque({'owner': 'owner1', 'project': 'projectB', 'timeout': 8})

    # launchue an item
    popped_item = redis_queue.launch()
    if popped_item:
        print(f"launchued item: {popped_item}")

    redis_queue.enque({'owner': 'owner1', 'project': 'projectC',
                       'timeout': 8, "command": "command"})

    popped_item = redis_queue.launch()
    if popped_item:
        print(f"launchued item: {popped_item}")

    # # Complete an item
    redis_queue.complete('item:1')

    # # Print current Redis data as JSON
    # print("Current Redis data as JSON:")
    # # redis_queue.print_data_as_json()
