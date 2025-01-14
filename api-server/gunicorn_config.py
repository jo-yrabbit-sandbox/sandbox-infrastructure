# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 120
worker_class = "sync"

# Configure logging
accesslog = "/home/ubuntu/api-server/current/api-server/logs/access.log"
errorlog = "/home/ubuntu/api-server/current/api-server/logs/error.log"
loglevel = "debug"  # Increased log level for debugging
# Add detailed logging
capture_output = True
enable_stdio_inheritance = True
