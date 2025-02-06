import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from schemas.logging import LogLevel, OperationLog, RedisOperation, SystemMetrics
from logging.handlers import RotatingFileHandler


class StructuredLogger:

    def __init__(self, service_name: str = 'app', log_level: str = LogLevel.INFO, log_dir: str = 'logs'):
        self.logger = logging.getLogger(service_name)
        self.service_name = service_name

        os.makedirs(log_dir, exist_ok=True) # Ensure logs directory exists
        file_handler = RotatingFileHandler(f'{log_dir}/{service_name}.log', maxBytes=10240, backupCount=10)
        self.logger.addHandler(file_handler)

        log_level_numeric = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level_numeric)

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.now(datetime.timezone.utc).isoformat(),
                'service': record.name,
                'level': record.levelname,
                'message': record.msg,
                'data': record.__dict__.get('data', {})
            }
            return json.dumps(log_data)

    def log_operation(self, operation: OperationLog) -> None:
        """Log a Redis operation with structured data"""
        self.logger.info(
            f"Redis operation: {operation['operation'].value}",
            extra={'data': operation}
        )

    def log_metrics(self, metrics: SystemMetrics) -> None:
        """Log system metrics"""
        self.logger.info(
            "System metrics collected",
            extra={'data': metrics}
        )