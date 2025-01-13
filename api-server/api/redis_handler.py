import redis
import time


MAX_MESSAGES=100  # TODO: Make configurable

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
                decode_responses=True,
                socket_timeout=5,  # 5 seconds timeout for operations
                socket_connect_timeout=5  # 5 seconds timeout for connection
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

        self.logger.info(f'Setting hash to {message_id=}, mapping: {message_data=}')
        try:
            self.redis_client.hset(message_id, mapping=message_data)
        except TimeoutError as e:
            self.logger.error(f"Redis timeout: {e}")
        except Exception as e:
            message = f'Failed to set hash to {message_id=}, mapping: {message_data} - {e.args}'
            self.logger.error(message)
            raise Exception(message)

        key = f"state:{state}:messages"
        self.logger.info(f'Adding to hash {message_id=} new key {key=}')
        try:
            self.redis_client.lpush(key, message_id)
        except TimeoutError as e:
            self.logger.error(f"Redis timeout: {e}")
        except Exception as e:
            message = f'Failed to add new key {key=} to hash {message_id=} - {e.args}'
            self.logger.error(message)
            raise Exception(message)
        
        try:
            self.redis_client.ltrim(key, 0, MAX_MESSAGES-1)
        except TimeoutError as e:
            self.logger.error(f"Redis timeout: {e}")
        except Exception as e:
            message = f'Failed to purge messages exceeding capacity ({MAX_MESSAGES}) - {e.args}'
            self.logger.error(message)
            raise Exception(message)

        self.logger.info(f'Successfully stored {message_id=}, mapping: {message_data}, key: {key}')
        return message_id