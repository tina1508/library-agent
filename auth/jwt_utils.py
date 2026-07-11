"""
Library AI Agent - JWT Utilities
Signs and verifies session tokens; no external JWT library required.
"""

import json
import hmac
import hashlib
import base64
import time
import logging
from datetime import datetime, timedelta
from config import app_config

logger = logging.getLogger(__name__)
_SECRET = app_config.jwt_secret.encode()


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def create_token(user_id: str, email: str, days: int = 7) -> str:
    """Create a signed JWT-like token."""
    header  = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64encode(json.dumps({
        "sub":   user_id,
        "email": email,
        "iat":   int(time.time()),
        "exp":   int(time.time()) + days * 86400,
    }).encode())
    sig = _b64encode(
        hmac.new(_SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


def verify_token(token: str) -> dict | None:
    """Verify signature and expiry; return payload dict or None."""
    try:
        header, payload, sig = token.split(".")
        expected = _b64encode(
            hmac.new(_SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_b64decode(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


def token_hash(token: str) -> str:
    """SHA-256 hex digest of a token (for storage)."""
    return hashlib.sha256(token.encode()).hexdigest()
