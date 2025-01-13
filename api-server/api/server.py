from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS  # TODO: Enable auth
import logging
from logging.handlers import RotatingFileHandler
import os

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
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
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

@app.route('/api/v1/hello', methods=['GET'])
def hello():
    print('Received request: hello')
    return jsonify({'status': 'healthy'})


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    print('Received request: health')
    result = ''

    if not redis_handler.redis_client:
        message = 'Redis client has not been initialized yet. Run `start` before interacting with it'
        app.logger.error(message)
        return jsonify({
            'status': 'unhealthy',
            'redis': 'not_started',
            'ping': result,
            'redis_host': os.getenv('REDIS_HOST', 'not_set')
        })

    try:
        result = redis_handler.redis_client.ping()
        return jsonify({
            'status': 'healthy',
            'redis': 'connected',
            'ping': result,
            'redis_host': os.getenv('REDIS_HOST', 'not_set')
            }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'redis': str(e),
            'ping': result,
            'redis_host': os.getenv('REDIS_HOST', 'not_set')
        })


@app.route('/debug-redis')
def debug_redis():
    import os
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    return {
        'redis_host': redis_host,
        'environment': dict(os.environ),
        'redis_client': str(redis_handler.redis_client)
    }


@app.route('/api/v1/messages/latest', methods=['GET'])
def get_latest_message():
    """Get latest message"""
    app.logger.info('Received: get_latest_message')
    try:
        state = request.args.get('state')  # TODO: Better to filter by bot_id to accommodate multiple bots
        if not state:
            return jsonify({'error': 'Missing required field `state`'}), 400

        app.logger.info(f'Processing request for latest message with {state=}')
        message = redis_handler.get_latest_message(state)
        print(f'Got latest message: {message}')
        return jsonify({'message': str(message)})

    except Exception as e:
        message = f'Failed to get latest message - {e.args[0]}'
        app.logger.error(message)
        return jsonify({'error': message}), 500


@app.route('/api/v1/messages', methods=['GET'])
def get_messages():
    """Get messages"""
    app.logger.info('Received: get_messages')
    try:
        # bot_id = request.args.get('bot_id')  # TODO: Better to filter by bot_id to accommodate multiple bots
        limit_str = request.args.get('limit')
        if not limit_str:
            return jsonify({'error': 'Missing required field `limit`'}), 400
        try:
            limit = int(limit_str)
        except Exception as e:
            raise Exception(f'Limit \"{limit_str}\" could not be converted to int')
        state = request.args.get('state')
        if not state:
            return jsonify({'error': 'Missing required field `state`'}), 400

        app.logger.info(f'Processing request for last {limit} messages with {state=}')
        messages = redis_handler.get_messages(state, limit=limit)

        app.logger.info(f'Successfully received last {limit} messages with {state=}')
        return jsonify({'messages': messages})

    except Exception as e:
        m = f'Error getting last {limit} messages - {e.args[0]}'
        app.logger.error(m)
        return jsonify({'error': m}), 500


@app.route('/api/v1/messages', methods=['POST'])  # TODO: Add following decorators later: @require_api_key @limiter.limit("30 per minute")
def store_message():
    """Store a new message"""
    print('Received request: store_message')
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['bot_id', 'message']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        bot_id = data['bot_id']

        # Validate message structure
        message = data['message']
        if not all(field in message for field in ['state', 'text', 'timestamp']):
            return jsonify({"error": "Invalid message structure"}), 400
        state = message['state']

        # Store message
        app.logger.info(f'Processing request to store message from {bot_id=} with {state=}')
        message_id = redis_handler.store_message(
            bot_id=bot_id,
            state=state,
            text=message['text'],
            timestamp=message['timestamp'],
        )

        app.logger.info(f'Successfully stored messages from {bot_id=} with {state=}')
        return jsonify({"success": True, "message_id": message_id}), 201

    except Exception as e:
        m = f"Error storing message - {str(e)}"
        app.logger.error(m)
        return jsonify({"error": f"Internal server error - {m}"}), 500
