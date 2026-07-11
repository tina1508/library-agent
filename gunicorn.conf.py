"""
Gunicorn production configuration for IBM Cloud / Code Engine deployment.
"""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
worker_class = "sync"
timeout = 120
keepalive = 5
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"

# Preload app for faster worker startup
preload_app = True
