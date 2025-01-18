import ast
import json
import redis
import time


TIMEOUT=900

class RedisHandler():

    BLANK = 'BLANK'
    INIT_ERROR = 'Redis client not initialized - did you run `start()`?'
    MAX_MESSAGES=10  # TODO: Make configurable
    REQUIRED_KEYS = ['bot_id', 'state']
    
    def __init__(self, logger):
        self.redis_client = None
        self.logger = logger


    def create_index(self, key, value=BLANK):
        if not key:
            error = 'Failed to create index due to key name is blank'
            self.logger.error(key)
            raise Exception(error)
        if not value:
            return ''
        if value == self.BLANK:
            self.logger.warning(f'Creating index for {key=} with value set to `{value}`')
        else:
            self.logger.debug(f'Creating index for {key=} with value set to `{value}`')
    
        return f'messages:by_{key}:{value}'


    def get_latest_message(self, query) -> str:
        """Get latest message"""
        self.logger.debug('Getting latest message')
        messages = self.get_messages(query, limit=1)
        if messages:
            return messages[0]  # unpack it
        else:
            return []


    def get_messages(self, query, limit=MAX_MESSAGES) -> list:
        """Get recent messages"""
        if not limit:
            error = f'Invalid arguments - number of messages to retrieve must be greater than 0 ({limit=})'
            self.logger.error(error)
            raise Exception(error)

        self.logger.debug(f'Getting up to {limit} messages')
        if not self.redis_client:
            raise Exception(self.INIT_ERROR)

        # Get indexes to find
        indexes = []
        for k,v in query.items():
            index = self.create_index(k, v)
            if index:
                indexes.append(index)

        # Do the search
        if len(indexes) > 1:
            message_ids = self.redis_client.sinter(indexes)
            self.logger.debug('Found {} messages matching indexes: {}'.format(len(message_ids), ', '.join(indexes)))
        elif len(indexes) == 1:
            message_ids = self.redis_client.smembers(indexes[0])
            self.logger.debug(f'Found {len(message_ids)} messages matching {indexes[0]}')
        else:
            warning = 'Could not find any messages matching indexes: {}'.format(', '.join(indexes))
            self.logger.warning(warning)
            return []

        # Get message_data
        messages = []
        remove_list = []
        for message_id in message_ids:
            message_data = self.redis_client.hgetall(message_id)
            if not message_data:
                remove_list.append(message_id)
                self.logger.warning(f'Ignoring {message_id=} due to message is empty. Queueing it for removal from database')
                continue
            elif type(message_data) is not dict:
                remove_list.append(message_id)
                self.logger.warning(f'Ignoring {message_id=} due to message type ({type(message_data)}) is not dict. Queueing it for removal from database')
            messages.append(message_data)
        self.logger.info('Retrieved {} messages matching indexes: {}'.format(len(messages), ', '.join(indexes)))

        # Clean up database
        if remove_list:
            try:
                self.remove_messages(remove_list, indexes)
            except Exception as e:
                self.logger.warning(f'Failed to remove ill-formatted messages - {e.args[0]}')

        # Trim if exceeding limit
        n = len(messages)
        if n == 0:
            return []
        elif (n > 0) and (limit == 1):
            return [messages[0]]
        elif (n > limit):
            messages = messages[0:limit]
            self.logger.info(f'Trimmed list of retrieved messages to {limit=} from {n}')
            return messages
        
        return messages  # list


    def remove_messages(self, remove_list, remove_keys):
        """Removes messages from database, skips removal on error"""
        self.logger.debug(f'Removing {len(remove_list)} messages from database')
        for message_id in remove_list:
            try:
                self.redis_client.delete(message_id)
                self.logger.info(f'Removed {message_id=} from database')
            except Exception as e:
                self.logger.warning(f'Skipping removal of {message_id=} from database - {e.args[0]}')

            try:
                self.redis_client.zrem('messages:by_timestamp', message_id)
                self.logger.info(f'Removed {message_id=} from time-indexed database')
            except Exception as e:
                self.logger.warning(f'Skipping removal of {message_id=} from time-indexed database - {e.args[0]}')

            for index in remove_keys:
                try:
                    self.redis_client.srem(index, message_id)
                    self.logger.info(f'Removed {message_id=} from {index=}')
                except Exception as e:
                    self.logger.warning(f'Skipping removal of {message_id=} from {index=} - {e.args[0]}')


    def start(self, redis_host, redis_port, redis_password):
        if self.redis_client:
            self.logger.error('Failed to start a new redis client due to client already exists')
            return

        try:
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_timeout=TIMEOUT,  # 5 seconds timeout for operations
                socket_connect_timeout=TIMEOUT  # 5 seconds timeout for connection
            )
        except Exception as e:
            error = 'Failed to start a new redis client - {}'.format(e.args[0])
            self.logger.error(error)
            raise Exception(error)
        
        self.redis_client = client
        self.logger.info(f'Successfully started redis client ({redis_host}:{redis_port})')


    def store_message(self, bot_id, state, text, timestamp) -> bool:
        """Store message in valid format"""
        if not self.redis_client:
            raise Exception(self.INIT_ERROR)

        # Set message id as unique hash
        # TODO: Replace with hash
        message_id = f'message:{int(time.time()*1000)}'

        # TODO: Document schema in doc/api-specification.md
        # Set message data fields
        message_data = {
            "bot_id" : bot_id,
            "state": state,
            "text" : text,
            "timestamp": timestamp
        }

        # Store message
        target = f'[{message_id}]: {message_data}'
        self.logger.debug(f'Storing {target}...')
        try:
            self.redis_client.hset(message_id, mapping=message_data)
        except TimeoutError as e:
            error = f"Failed to store {target} due to redis timeout - {e.args[0]}"
            self.logger.error(error)
            raise Exception(error)
        except Exception as e:
            error = f'Failed to store {target} - {e.args[0]}'
            self.logger.error(error)
            raise Exception(error)

        # Create indexes
        for key in self.REQUIRED_KEYS:
            index = self.create_index(key, message_data[key])
            if not index:
                raise Exception(f'Message is missing required {key=}')
            try:
                self.redis_client.sadd(index, message_id)
            except TimeoutError as e:
                self.logger.error(f"Redis timeout: {e}")
            except Exception as e:
                error = f'Failed to add {index=} to {message_id=} - {e.args[0]}'
                self.logger.error(error)
                raise Exception(error)
            self.logger.debug(f'Added {index=} to {message_id=}')
        
        # Add by time-based index
        try:
            self.redis_client.zadd('messages:by_timestamp', {message_id: message_data['timestamp']})
        except TimeoutError as e:
            self.logger.error(f"Redis timeout: {e}")
        except Exception as e:
            error = f'Failed to add by timestamp {message_id=} - {e.args[0]}'
            self.logger.error(error)
            raise Exception(error)
        self.logger.debug('Added message_id={} by timestamp ({})'.format(message_id, message_data['timestamp']))

        # Purge excess messages
        try:
            all_message_ids = self.redis_client.zrange("messages:by_timestamp", 0, -1)
        except TimeoutError as e:
            self.logger.error(f"Redis timeout: {e}")
        except Exception as e:
            error = f'Failed to purge messages matching {index=} which exceed capacity ({self.MAX_MESSAGES}) - {e.args[0]}'
            self.logger.error(error)
            raise Exception(error)
        
        n = len(all_message_ids)
        if n > self.MAX_MESSAGES:
            remove_list = all_message_ids[:n - self.MAX_MESSAGES]
            self.remove_messages(remove_list)

        self.logger.info(f'Stored {target}')
        return message_id