import redis
import time

class RedisHandler():

    def __init__(self, logger):
        self.redis_client = None
        self.logger = logger


    def get_latest_message(self, state) -> str:
        """Get latest message"""
        messages = self.get_messages(state, limit=1)
        return messages[0]  # unpack it


    def get_messages(self, state, limit=2) -> list:
        """Get recent messages"""
        key = f"state:{state}:messages"
        
        # Get message_ids
        message_ids = self.redis_client.lrange(key, 0, limit-1)
        if not message_ids:
            raise Exception(f'Failed to get latest {limit} messages using key {key}')

        # Get message_data
        messages = []
        for message_id in message_ids:
            message_data = self.redis_client.hgetall(message_id)
            if message_data:
                messages.append(message_data)

        return messages  # list


    def start(self, redis_host, redis_port, redis_password):
        if self.redis_client:
            self.logger.error('Failed to start a new redis client due to a client already exists')
            return

        try:
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
        except Exception as e:
            self.logger.error('Failed to start a new redis client - {}', e.args)
        
        self.redis_client = client
        self.logger.info(f'Successfully started redis client ({redis_host}:{redis_port})')


    def store_message(self, bot_id, state, text, timestamp) -> bool:
        """Store message in valid format"""
        if not self.redis_client:
            raise Exception('ERROR: Client has not been initialized yet. Run `start` to start the client before interacting with it')

        # Set message id as unique hash
        # TODO: Replace with hash
        message_id = f'msg:{int(time.time()*1000)}'

        # TODO: Document schema in doc/api-specification.md
        # Set message data fields
        message_data = {
            "bot_id" : bot_id,
            "state": state,
            "text" : text,
            "timestamp": timestamp
        }
        self.redis_client.hset(message_id, mapping=message_data)

        key = f"state:{state}:messages"
        try:
            self.redis_client.lpush(key, message_id)
        except Exception as e:
            raise Exception('Failed to store message - {}', e.args)
        
        # TODO: Make configurable
        try:
            self.redis_client.ltrim(key, 0, 99)
        except Exception as e:
            raise Exception('Failed to purge messages exceeding capacity (100) - {}', e.args)

        self.logger.info(f'Successfully stored {message_id=}')
        return message_id