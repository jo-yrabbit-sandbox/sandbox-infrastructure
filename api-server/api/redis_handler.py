import json
import logging
from redis.asyncio import Redis
from schemas.message import Message


TIMEOUT=900

class RedisHandler():

    def __init__(self, logger, redis_host: str = 'localhost', redis_port: int = 6379, redis_password: str = ''):
        self.logger = logger
        self.prefixes = {
            'message': 'msg:',
            'hash': 'hash:',    # For deduplication
            'index': {
                'type': 'idx:type:',
                'source': 'idx:source:',
                'tag': 'idx:tag:'
            }
        }
        self._init_redis_client(redis_host, redis_port, redis_password)

    async def store_message(self, message: Message) -> str:
        try:
            pipeline = self.redis_client.pipeline()
            # Store message
            msg_key = f"{self.prefixes['message']}{message['id']}"
            pipeline.set(msg_key, json.dumps(message))

            # Store content hash for deduplication
            hash_key = f"{self.prefixes['hash']}{message['metadata']['content_hash']}"
            pipeline.set(hash_key, message['id'])

            # Basic indexes
            source_key = f"{self.prefixes['index']['source']}{message['metadata']['source_id']}"
            type_key = f"{self.prefixes['index']['type']}{message['metadata']['msg_type']}"
            pipeline.sadd(source_key, message['id'])
            pipeline.sadd(type_key, message['id'])

            # Tag indexes
            for tag in message['metadata'].get('tags', []):
                tag_key = f"{self.prefixes['index']['tag']}{tag}"
                pipeline.sadd(tag_key, message['id'])

            await pipeline.execute()
            return message['id']

        except Exception as e:
            self.logger.structured(
                logging.ERROR,
                "Failed to store message",
                error=str(e),
                message_id=message['id']
            )
            raise

    def _init_redis_client(self, redis_host, redis_port, redis_password):
        try:
            self.redis_client = Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_timeout=TIMEOUT,  # 5 seconds timeout for operations
                socket_connect_timeout=TIMEOUT  # 5 seconds timeout for connection
            )
            self.logger.info(f'Successfully started redis client ({redis_host}:{redis_port})')
        except Exception as e:
            error = 'Failed to start a new redis client - {}'.format(e.args[0])
            self.logger.structured(
                logging.ERROR,
                f'{error}',
                error=str(e)
            )
            raise Exception(error)