import logging
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  # TODO: Enable auth
import hashlib

from api.redis_handler import RedisHandler
from structured_logging.logging_setup import setup_structured_logging
from schemas.message import MessageType, Message

# Load environment variables if ../.env exists
dotenv = os.path.isfile(os.path.join(
    os.path.dirname(os.path.dirname(
        os.path.normpath(__file__))), '.env'))
if os.path.isfile(dotenv):
    load_dotenv(dotenv)

# Note: If you change attribute name `app` for this flask server,
# make sure you edit the Dockerfile and gunicorn command arg too
app = Flask(__name__)
setup_structured_logging(app, service_name='app', log_level=os.getenv('LOG_LEVEL', 'INFO'), log_dir='logs')
app.logger.info('API server startup')

# Note: For debugging, replace with CORS(app)
CORS(app, resources={
    r'/api/*': {
        'origins': [
            f'{os.getenv("WEBSITE_URL", "http://localhost:8000")}',
            'your-production-domain.com'
            ],
        'methods': ['GET'],
        'allow_headers': ['Content-Type']
    }
})

# Configure redis
try:
    redis_handler = RedisHandler(app.logger,
                                 redis_host=os.getenv('REDIS_HOST', 'localhost'),
                                 redis_port=int(os.getenv('REDIS_PORT', 6379)),
                                 redis_password=os.getenv('REDIS_PASSWORD'))
except Exception as e:
    app.logger.error(f'Failed to connect to redis - {str(e)}')

####
# Routes
####
API_PREFIX='/api/v1'

#### utils
def get_schema(status='', error='') -> dict:
    d = dict.fromkeys(['status', 'error'], '')
    if status:
        d.update({'status': status})
    if error:
        d.update({'error': error})
    return d

#### Health checks
@app.route('/hello', methods=['GET'])
def hello():
    app.logger.debug(f'Received request: `{request.endpoint}` ..., hello!')
    return jsonify(get_schema(status='healthy'))

@app.route('/health', methods=['GET'])
def health():
    app.logger.debug(f'Received request: `{request.endpoint}`')

    try:
        if not redis_handler.redis_client.ping():
            raise Exception()
        d = get_schema(status='healthy')
        d.update({'redis': 'connected'})
        return jsonify(d), 200
    except Exception as e:
        error = 'Failed to ping redis client - `/debug-redis` for more info'
        app.logger.error(error)
        d = get_schema(status='unhealthy', error=error)
        d.update({'redis' : f'not connected - {str(e)}'})
        return jsonify(d)

@app.route('/debug-redis', methods=['GET'])
def debug_redis():
    app.logger.debug(f'Received request: `{request.endpoint}`')
    d = get_schema()  # Keep `status` and `error` fields blank since this is a config dump
    try:
        data = {
            'redis_host': os.getenv('REDIS_HOST', 'localhost'),
            'environment': str(dict(os.environ)),
            'redis_client': str(redis_handler.redis_client)
        }
        d.update(data)
    except Exception as e:
        d.update(error=str(e))
    return jsonify(d)

### Messages
API_PREFIX_MESSAGES = f'{API_PREFIX}/messages'
TIMESTAMP_FORMAT='%Y-%m-%d_%H:%M:%S'

def get_timestamp(input) -> int:
    """Return timestamp as seconds since epoch (int)"""
    if 'test' in str(input):
        return int(time.time())
    elif type(input) is int:
        return input
    elif type(input) is float:
        return int(input)
    elif type(input) is str:
        try:
            d=datetime.strptime(input, TIMESTAMP_FORMAT)
            return int(d.timestamp())
        except Exception as e:
            app.logger.warning(f'Failed to parse timestamp \'{input}\'. Defaulting to current timestamp')
    else:
        app.logger.warning(f'Invalid timestamp input \'{input}\'. Defaulting to current timestamp')
    return int(time.time())

def validate(input, required_keys):
    if type(required_keys) is not list:
        raise Exception(f'Ivalid argument - `required_keys` must be passed in as list, but got {type(required_keys)}')
    if type(input) is not dict:
        raise Exception(f'Ivalid argument - `input` must be passed in as dict, but got {type(input)}')
    
    missing_keys = []
    for k in required_keys:
        if k not in input.keys():
            missing_keys.append(k)
    if missing_keys:
        raise Exception('Invalid message - missing required keys: {}'.format(', '.join(missing_keys)))

def create_text_message(text: str, source_id: str, tags: list[str] = None) -> Message:
    """Create a text message with proper structure"""
    message_id = f'{int(time.time()*1000)}'  # TODO: Set message id as unique hash
    return {
        'id': message_id,
        'content': {
            'text': text,
            'language': 'en'  # Could be detected automatically
        },
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'source_id': source_id,
            'msg_type': MessageType.TEXT.value,
            'thread_id': None,
            'tags': tags or [],
            'size_bytes': len(text.encode('utf-8')),
            'content_hash': hashlib.sha256(text.encode('utf-8')).hexdigest()
        }
    }

@app.route(API_PREFIX_MESSAGES, methods=['POST'])  # TODO: Add following decorators later: @require_api_key @limiter.limit("30 per minute")
async def store_message():
    app.logger.debug('Storing message...')

    try:
        data = request.get_json()
        validate(data, ['bot_id', 'message'])
    except Exception as e:
        error = f'Failed to parse POST request data into json - {str(e)}'
        app.logger.error(error)
        return jsonify(get_schema(status='fail', error=error)), 400

    # Store message
    try:
        # TODO: Use Telegram adapter here
        source_id = f"telegram_bot_{data['bot_id']}"
        tags = [data['message']['state']]  # TODO: swap for data.get('tags', [])
        text = data['message']['text']
        message = create_text_message(text, source_id, tags)

        target = 'message from bot_id={}. content={}, metadata={}'.format(data['bot_id'], text, message['metadata'])
        app.logger.structured(
            logging.INFO,
            f'Received {target}',
            source_id=message['metadata']['source_id'],
            content_type=message['metadata']['msg_type'],
            size=message['metadata']['size_bytes']
        )

        # TODO: Refactor redis_handler to that new design with CRUD separation, etc.
        success = await redis_handler.store_message(message)

        if success:
            app.logger.info(f'Stored {target}')
            d = get_schema(status='success')
            d.update({'data': {'message': message}})
            return jsonify(d), 201
        else:
            d = get_schema(status='fail', error=f'Failed to store {target}')
            return jsonify(d), 500

    except Exception as e:
        error = f"Failed to store message due to internal server error - {str(e)}"
        app.logger.structured(
            logging.ERROR,
            f'{error}',
            error=str(e),
            error_type=type(e).__name__
        )
        return jsonify(get_schema(status='fail', error=error)), 500