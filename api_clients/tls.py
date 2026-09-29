"""TLS verification for every HTTP call this repo makes.

Off unless SSL_VERIFY is true, 1 or yes in .env. The QA server's
certificate has not been proven from a clean machine, and against a
self-signed certificate a verified handshake fails and reads as "could
not reach the API". One reader for the clients, the fixtures and the
tools, so they cannot disagree. It reads the environment at call time,
so a .env loaded after import still counts.
"""
from __future__ import annotations

import os


def ssl_verify() -> bool:
    """True when SSL_VERIFY is true, 1 or yes (any case). False when unset."""
    return os.getenv("SSL_VERIFY", "").strip().lower() in ("true", "1", "yes")
