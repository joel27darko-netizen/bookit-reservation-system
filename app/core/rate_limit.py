"""
Minimal in-memory rate limiter for auth endpoints.

Tracks failed attempts per (client IP, email) key with a sliding window.
This is process-local (fine for a single-instance deployment / demo); a
multi-instance production deployment should back this with Redis instead.
"""
import time
import threading
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException, status

# key -> list of failure timestamps (seconds)
_attempts: Dict[str, List[float]] = defaultdict(list)
_lock = threading.Lock()

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60  # 15 minutes
LOCKOUT_SECONDS = 15 * 60


def _key(ip: str, identifier: str) -> str:
    return f"{ip}:{identifier.lower()}"


def check_rate_limit(ip: str, identifier: str) -> None:
    """Raise 429 if this ip+identifier has too many recent failures."""
    key = _key(ip, identifier)
    now = time.time()
    with _lock:
        recent = [t for t in _attempts[key] if now - t < WINDOW_SECONDS]
        _attempts[key] = recent
        if len(recent) >= MAX_ATTEMPTS:
            retry_after = int(LOCKOUT_SECONDS - (now - recent[0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many attempts. Try again in {max(1, retry_after // 60)} minute(s).",
            )


def record_failure(ip: str, identifier: str) -> None:
    key = _key(ip, identifier)
    with _lock:
        _attempts[key].append(time.time())


def record_success(ip: str, identifier: str) -> None:
    """Clear the failure history for this key on a successful attempt."""
    key = _key(ip, identifier)
    with _lock:
        _attempts.pop(key, None)
