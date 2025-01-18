import os
import time
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  # TODO: Enable auth

import logging
from logging.handlers import RotatingFileHandler

from api.redis_handler import RedisHandler

# Load environment variables if ../.env exists
dotenv = os.path.isfile(os.path.join(
    os.path.dirname(os.path.dirname(
        os.path.normpath(__file__))), '.env'))
if os.path.isfile(dotenv):
    load_dotenv(dotenv)

# Note: If you change attribute name `app` for this flask server,
# make sure you edit the Dockerfile and gunicorn command arg too
app = Flask(__name__)

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

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'DEBUG')
numeric_level = getattr(logging, log_level.upper(), logging.INFO)
os.makedirs('logs', exist_ok=True) # Ensure logs directory exists
# Set up file handler
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
file_handler.setLevel(numeric_level)
# Configure app logger
app.logger.addHandler(file_handler)
app.logger.setLevel(numeric_level)
app.logger.info('API server startup')

# Configure redis
try:
    redis_handler = RedisHandler(logger=app.logger)
    redis_handler.start(redis_host=os.getenv('REDIS_HOST', 'localhost'),
                        redis_port=int(os.getenv('REDIS_PORT', 6379)),
                        redis_password=os.getenv('REDIS_PASSWORD'))
    app.logger.info('Connected to redis')
except Exception as e:
    app.logger.info(f'Failed to connect to redis - {str(e)}')


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
    app.logger.debug(f'Received request: {request.endpoint}... hello!')
    return jsonify(get_schema(status='healthy'))

@app.route('/health', methods=['GET'])
def health():
    app.logger.debug(f'Received request: {request.endpoint} with args: {dict(request.args)}')
    d = get_schema(status='unhealthy')
    d.update({'redis': ''})

    if not redis_handler.redis_client:
        app.logger.error(redis_handler.INIT_ERROR)
        d.update({'redis' : 'not initialized'})
        d.update({'error' : redis_handler.INIT_ERROR})
        return jsonify(d)

    try:
        if redis_handler.redis_client.ping():
            d.update({'status': 'healthy'})
        d.update({'redis': 'connected'})
        return jsonify(d), 200
    except Exception as e:
        error = 'Failed to ping redis client - `/debug-redis` for more info'
        app.logger.error(error)
        d.update({'redis' : f'not connected - {str(e)}'})
        d.update({'error' : error})
        return jsonify(d)

@app.route('/debug-redis', methods=['GET'])
def debug_redis():
    app.logger.debug(f'Received request: {request.endpoint}')
    d = get_schema()
    d.update({'redis_host': os.getenv('REDIS_HOST', 'localhost')})
    d.update({'environment': str(dict(os.environ))})
    d.update({'redis_client': str(redis_handler.redis_client)})
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

# TODO: Move this to redis_handler
def get_query(this_request):
    required_args = ['bot_id', 'state']

    query = dict().fromkeys(required_args)
    error = ''

    try:
        app.logger.debug(f'Received request: {this_request.endpoint} with args: {dict(this_request.args)}')
    except Exception as e:
        error = f'Unexpected error: invalid flask request object'
        app.logger.error(error)
        return False, error, {}, {}

    for arg in query.keys():
        try:
            query.update({arg: this_request.args.get(arg)})
        except Exception as e:
            error = f'Invalid request - missing required argument `{arg}` - {str(e)}'
            app.logger.error(error)
            return False, error, {}, {} 

    return True, error, query


@app.route(f'{API_PREFIX_MESSAGES}/latest', methods=['GET'])
def get_latest_message():
    """Get latest message"""
    result, error, query = get_query(request)
    if not result:
        return jsonify(get_schema(status='fail', error=error)), 400

    target = 'latest message from bot_id={} with state={}'.format(query['bot_id'], query['state'])
    try:
        app.logger.debug(f'Getting {target}')

        message = redis_handler.get_latest_message(query)
        if not message:
            raise Exception('No messages found matching query')
        app.logger.info(f'Got {target}: {message}')

        d = get_schema(status='success')
        d.update({'data': str(message)})  # TODO: parse message into json format with fields `message` + required_args
        return jsonify(d)

    except Exception as e:
        error = f'Failed to get {target} - {e.args[0]}'
        app.logger.error(error)
        return jsonify(get_schema(status='fail', error=error)), 500


@app.route(API_PREFIX_MESSAGES, methods=['GET'])
def get_messages():
    result, error, query = get_query(request)
    if not result:
        return jsonify(get_schema(status='fail', error=error)), 400

    # Parse limit from argument
    try:
        limit_str = request.args.get('limit')
        if not limit_str:
            limit = redis_handler.MAX_MESSAGES
            warning = f'Request is missing argument `limit`. Setting it to default value (max number of stored messages: {limit})'
            app.logger.warning(warning)
        else:
            limit = int(limit_str)
    except Exception as e:
        limit = redis_handler.MAX_MESSAGES
        warning = f'Failed to parse limit from request into valid int. Setting it to default value (max number of stored messages: {limit}) - {e.args[0]}'
        app.logger.warning(warning)

    target = 'messages from bot_id={} with state={}'.format(query['bot_id'], query['state'])
    try:
        app.logger.debug(f'Getting up to {limit} {target}')
        messages = redis_handler.get_messages(query, limit=limit)
        app.logger.info(f'Found {len(messages)} {target}')
        d = get_schema(status='success')
        d.update({'data': messages})
        return jsonify(d)

    except Exception as e:
        error = f'Failed to get {target} - {e.args[0]}'
        app.logger.error(error)
        return jsonify(get_schema(status='fail', error=error)), 500


@app.route(API_PREFIX_MESSAGES, methods=['POST'])  # TODO: Add following decorators later: @require_api_key @limiter.limit("30 per minute")
def store_message():
    app.logger.debug('Storing message...')
    def validate(input, required_keys) -> str:
        if type(required_keys) is not list:
            return False, f'Ivalid argument - `required_keys` must be passed in as list, but got {type(required_keys)}'
        if type(input) is not dict:
            return False, f'Ivalid argument - `input` must be passed in as dict, but got {type(input)}'
        
        missing_keys = []
        for k in required_keys:
            if k not in input.keys():
                missing_keys.append(k)
        if missing_keys:
            return False, 'Invalid message - missing required keys: {}'.format(', '.join(missing_keys))

        return True, ''

    try:
        data = request.get_json()
    except Exception as e:
        error = f"Failed to parse POST request data into json - {str(e)}"
        app.logger.error(error)
        return jsonify(get_schema(status='fail', error=error)), 400

    try:
        # Validate data structure
        result, error = validate(data, ['bot_id', 'message'])
        if not result:
            raise Exception(error)

        # Validate message structure
        result, error = validate(data['message'], ['state', 'text', 'timestamp'])
        if not result:
            raise Exception(error)

    except Exception as e:
        error = f"Failed to validate input message - {str(e)}"
        app.logger.error(error)
        return jsonify(get_schema(status='fail', error=error)), 400

    # Store message
    try:
        target = 'message from bot_id={} with state={}'.format(data['bot_id'], data['message']['state'])
        app.logger.debug(f'Processing request to store {target}')
        message_id = redis_handler.store_message(
            bot_id=data['bot_id'],
            state=data['message']['state'],
            text=data['message']['text'],
            timestamp=get_timestamp(data['message']['timestamp'])
        )

        app.logger.info(f'Stored {target} as {message_id=}')
        d = get_schema(status='success')
        d.update({'data': {'message_id': message_id}})
        return jsonify(d), 201

    except Exception as e:
        error = f"Failed to store message due to internal server error - {str(e)}"
        return jsonify(get_schema(status='fail', error=error)), 500
