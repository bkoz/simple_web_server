"""Gunicorn configuration for production deployment"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'  # Use 'gevent' or 'eventlet' for async
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (prevent memory leaks)
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'simple-web-server'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Performance tuning
preload_app = True  # Load application code before worker processes fork
