import logging
from flask import Flask, request, has_request_context
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter that includes request context when available"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log data
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'module': record.module,
            'function': record.name,
            'message': record.getMessage()
        }

        # Add request context if available
        if has_request_context():
            log_data.update({
                'request_id': request.headers.get('X-Request-ID'),
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
            })

        # Add extra data if provided
        if hasattr(record, 'data'):
            log_data['data'] = record.data

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class SafeRotatingFileHandler(RotatingFileHandler):
    """Handles the file lock issue on Windows by trying multiple times with a delay"""
    
    def rotate(self, source, dest):
        """Rotate the file, retrying if it fails due to file lock"""
        for _ in range(5):  # Try 5 times
            try:
                # If dest exists, remove it first
                if os.path.exists(dest):
                    os.remove(dest)
                os.rename(source, dest)
                break
            except PermissionError:
                import time
                time.sleep(0.1)  # Wait a bit before retrying
        else:
            # If we get here, we failed all retries
            # Log this but don't crash
            print(f"Failed to rotate log file from {source} to {dest}")


def setup_structured_logging(app: Flask, service_name: str = 'app', log_level: str = logging.INFO, log_dir: str = 'logs') -> None:
    """Configure Flask app logger for structured logging"""
    
    # Remove default handlers
    app.logger.handlers = []
    
    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(StructuredJsonFormatter())
    app.logger.addHandler(console_handler)
    
    # Optionally add file handler
    os.makedirs(log_dir, exist_ok=True) # Ensure logs directory exists
    file_handler = SafeRotatingFileHandler(f'{log_dir}/{service_name}.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(StructuredJsonFormatter())
    app.logger.addHandler(file_handler)
    
    # Set default level
    log_level_numeric = getattr(logging, log_level.upper(), logging.INFO)
    app.logger.setLevel(log_level_numeric)

    # Extend Flask logger with structured logging methods
    def log_structured(self, level: int, message: str, **data: Any) -> None:
        """Log a message with structured data"""
        if self.isEnabledFor(level):
            record = self.makeRecord(
                self.name,
                level,
                '(structured)',
                0,
                message,
                None,
                None
            )
            record.data = data
            self.handle(record)

    # Add method to logger
    app.logger.__class__.structured = log_structured
