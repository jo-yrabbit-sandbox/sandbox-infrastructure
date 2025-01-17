## How to run tests

During development, you may want to run some basic tests. This how-to explains how to run the following scenarios:
* Test `api-server` in standalone (without `redis`)
  * Sanity test that the Flask application (`api-server`) is running without worrying about its connection to the backend database
* Test `api-server` with `redis`
  * Test that your Flask application (`api-server`) is correctly connected to the backend database (`redis`)

### Test `api-server` in standalone (without `redis`)
Below are the two ways explained here:
  * (Option 1) Run the Flask application directly with python
  * (Option 2) Run it in a container (e.g. test your Dockerfile)

#### Option 1: Run directly using python
No Dockerfile needed
1. Confirm `REDIS_HOST` is not set in your environment
```sh
echo $REDIS_HOST  # Should return blank
```
2. Run the application only, no redis backend
```sh
cd <top-level>  # top-level directory containing "run.py"
python -m app  # Will continue to run until Ctrl+C
```
3. Confirm route `hello` is healthy
```sh
curl localhost:5000/hello
```

#### Option 2: Run api-server in container
This is for testing your `Dockerfile`
1. Confirm `REDIS_HOST` is not set in your `.env` file
```sh
source .env
echo $REDIS_HOST  # Should return blank
```
2. Run `api-server` in Docker container
```sh
# Build the image
docker build -t api-server .

# Run container
docker run -d -p 5000:5000 --env-file .env --name api-server api-server
```
3. Confirm route `hello` is healthy
```sh
curl localhost:5000/hello
```
4. Debug commands
```sh
docker ps  # Is your container running?
docker ps -a  # Is your container stopped?
docker logs api-server  # Look at logs to see why container stopped

# Teardown
docker stop api-server
docker rm api-server
```

### Test `api-server` with `redis`

Here we will describe how to locally host the Flask application and redis backend so we can test their connection
* (Recommended) Start both services with `docker-compose.yml`
* (Not recommended) Run `api-server` in standalone, and run `redis` as separate docker container on `localhost:6379`

#### Option 1: How to run your containers using docker compose
This is for testing your `docker-compose.yml`. We assume that you have the following already working:
* `Dockerfile` for `api-server` exists and runs in standalone

1. Navigate to parent directory containing your `docker-compose.yml`, `Dockerfile`, `.env` files
2. Confirm * `.env` file has `REDIS_HOST=redis` (matching whatever you specified in `docker-compose.yml`)
```sh
source .env
echo $REDIS_HOST  # Should return redis
```
3. Start your containers
```sh
docker-compose up

# If you've changed source code
docker compose up --build --force-recreate
```
4. Confirm routes `hello` and `health` are both healthy
```sh
curl localhost:5000/hello  # Just confirms api-server is running, no connection needed
curl localhost:5000/health  # Checks connection to redis as well

# Troubleshooting connection issues
curl localhost:5000/debug-redis  # Dump redis configurations
```

5. 
6. Teardown
3. Stop your containers
```sh
docker-compose down
```

#### Test endpoints
1. Store two test messages
  * For both test messages, `cat tests/test_message_<#>.json` to confirm content
```json
{
  "bot_id": "test_bot_id",
  "message": {
    "state": "test_state",
    "text": "test_text_<#>",
    "timestamp": "test_timestamp_<#>"
    }
}
```
  * Make `POST` request with url: http://localhost:5000/api/v1/messages
```sh
curl -0 -v POST <url> \
  -H "Content-Type: application/json; charset=utf-8" \
  -d @tests/test_message_<#>.json
```
  * Expected responses should show that the message_ids are unique per stored message
```json
// First stored message
{"data":{"message_id":"msg:123"},"error":"","status":"success"}

// Second stored message
{"data":{"message_id":"msg:456"},"error":"","status":"success"}
```

2. Get latest message should return second message, not first
  * Make `GET` request with url: http://localhost:5000/api/v1/messages/latest?bot_id=test_bot_id&state=test_state
```sh
curl -X GET "<url>"
```
  * Expected response:
```json
// Should be returning second stored message (test_text_2, test_timestamp_2), not the first
{"data":"{'bot_id': 'test_bot_id', 'state': 'test_state', 'text': 'test_text_2', 'timestamp': 'test_timestamp_2'}","error":"","status":"success"}
```