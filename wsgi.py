"""
Library AI Agent — Application factory shim for gunicorn.
Gunicorn uses: gunicorn "main:create_app()"
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from api.app import create_app  # noqa: F401 — re-exported for gunicorn
