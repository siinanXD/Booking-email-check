"""Gemeinsamer Flask-Limiter (App-Factory-kompatibel)."""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, storage_uri="memory://")
