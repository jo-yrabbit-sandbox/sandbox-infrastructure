## How to run tests

During development, you may want to run some basic tests. This how-to explains how to run the following scenarios:
* `Test without redis`
  * Sanity test that the Flask application (`api-server`) is running without worrying about its connection to the backend database
* `Test with redis`
  * Test that your Flask application (`api-server`) is correctly connected to the backend database (`redis`)

### Test without redis
Below are the two ways explained here:
  * Run the Flask application directly with python
  * Run it in a container (e.g. test your Dockerfile)

#### Option 1: Run directly using python
Update `.env` file so that `REDIS_HOST=localhost`
```sh
cd <top-level>  # top-level directory containing "run.py"
python -m app
```

#### Option 2: Run api-server in container
This is for testing your `Dockerfile` and assumes that it exists.
1. Navigate to parent directory containing your `Dockerfile` and `.env` file
2. Update `.env` file so that `REDIS_HOST=redis` (or match whatever you specified in your `Dockerfile`)
3. Build the image, then run a containter using that image
```
# Build the image
docker build -t api-server .

# Run container
docker run -d \
  -p 5000:5000 \
  --env-file .env \
  --name api-server \
  api-server
```

##### Troubleshooting
```sh
docker ps  # Is your container running?
docker ps -a  # Is your container stopped?
docker logs api-server  # Look at logs to see why container stopped

# Teardown
docker stop api-server
docker rm api-server
```

#### Sanity test
* Url: http://localhost:5000/api/v1/health
* Curl command: `curl -X GET <url>`
Expected response:
```json
{"status":"healthy"}
```

### Test with redis

Here we will describe how to run both Flask application and redis backend locally
* (Recommended) Start both services with `docker-compose.yml`
* (Not recommended) Run `api-server` in standalone, and run `redis` as separate docker container on `localhost:6379`

#### Option 1: How to run your containers with docker compose
1. This is for testing your `docker-compose.yml`. We assume that you have the following already working:
* `Dockerfile` for `api-server` exists
* `.env` file has `REDIS_HOST=redis` matches whatever you specified in your `Dockerfile`
2. Navigate to parent directory containing your `docker-compose.yml`, `Dockerfile`, `.env` files
3. Start your containers
```sh
cd <top-level>  # top-level directory containing Dockerfile
docker-compose up

# If you've changed source code
docker compose up --build --force-recreate
```

#### Option 2: Run in standalone

1. Refer to previous section to run api-server in container
2. Run vanilla `redis` in another container on `localhost:6379`
* Install redis in Docker
```sh
# Pull the Redis image
docker pull redis

# Run Redis container
# If running locally, configurations are:
#   - REDIS_HOST="localhost"
#   - REDIS_PORT=6379
#   - REDIS_PASSWORD=""
docker run --name local-redis -p 6379:6379 -d redis

# To check if it's running
docker ps

# To see Redis logs
docker logs local-redis
```

* When you're done, stop and remove the Redis container
```sh
docker stop local-redis
docker rm local-redis
```

#### Test endpoints
1. Store a message
  * Create `test_message.json` file
```json
{
  "bot_id": "test_bot_id",
  "message": {
    "state": "test_state",
    "text": "test_text",
    "timestamp": "test_timestamp"
  }
}
```
  * Make `POST` request with url: http://localhost:5000/api/v1/messages
```sh
curl -0 -v POST <url> \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @test_message.json
```
  * Expected responses
```json
{"message_id":"msg:123","success":true}
```

2. Get latest message
  * Make `GET` request with url: http://localhost:5000/api/v1/messages/latest?state=test_state
```sh
curl -X GET <url>
```
  * Expected response:
```json
{"message":"{'bot_id': 'test_bot_id', 'state': 'test_state', 'text': 'test_text', 'timestamp': 'test_timestamp'}"}
```
* If no messages have been stored in redis, error is expected because redis database has nothing stored in it at this time
```json
{"error":"Error getting latest message - Failed to get latest 1 messages using key state:test_state:messages"}
```
