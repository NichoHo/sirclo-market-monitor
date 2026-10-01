import collections
import functools
import math
import threading
import time
from typing import Dict, Optional, Tuple

from flask import current_app, jsonify, request


def get_client_ip() -> str:
    """Extract client IP address, supporting X-Forwarded-For headers."""
    if not request:
        return "127.0.0.1"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Stores request timestamps per (client_ip, bucket) key.
    """

    def __init__(self):
        self._history: Dict[Tuple[str, str], collections.deque] = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()

    def check(self, ip: str, bucket: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Check if request is within limit for the given window (in seconds).
        Returns (allowed: bool, retry_after: int).
        """
        with self._lock:
            now = time.time()
            timestamps = self._history[(ip, bucket)]
            cutoff = now - window

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= limit:
                oldest = timestamps[0]
                retry_after = max(1, int(math.ceil(oldest + window - now)))
                return False, retry_after

            timestamps.append(now)
            return True, 0

    def reset(self):
        """Clear all recorded request history."""
        with self._lock:
            self._history.clear()


class InFlightLock:
    """
    Thread-safe in-memory mutex tracking concurrent active requests
    per (client_ip, endpoint).
    """

    def __init__(self):
        self._active: set[Tuple[str, str]] = set()
        self._lock = threading.Lock()

    def acquire(self, ip: str, endpoint: str) -> bool:
        """Attempt to acquire active lock. Returns True if acquired, False if already busy."""
        with self._lock:
            key = (ip, endpoint)
            if key in self._active:
                return False
            self._active.add(key)
            return True

    def release(self, ip: str, endpoint: str):
        """Release active lock."""
        with self._lock:
            self._active.discard((ip, endpoint))

    def reset(self):
        """Clear all active locks."""
        with self._lock:
            self._active.clear()


rate_limiter = SlidingWindowRateLimiter()
in_flight_guard = InFlightLock()


def reset_rate_limits():
    """Helper to clear rate limiter history (useful in tests)."""
    rate_limiter.reset()


def reset_in_flight_locks():
    """Helper to clear concurrent locks (useful in tests)."""
    in_flight_guard.reset()


def is_rate_limit_enabled() -> bool:
    """Check if rate limiting is currently enabled in application configuration."""
    if not current_app:
        return True
    if "RATELIMIT_ENABLED" in current_app.config:
        return bool(current_app.config["RATELIMIT_ENABLED"])
    # Default to False under Flask TESTING mode to avoid interfering with standard API tests
    if current_app.config.get("TESTING", False):
        return False
    return True


def is_concurrent_lock_enabled() -> bool:
    """Check if concurrent in-flight guard is enabled."""
    if not current_app:
        return True
    if "CONCURRENT_LOCK_ENABLED" in current_app.config:
        return bool(current_app.config["CONCURRENT_LOCK_ENABLED"])
    return True


def rate_limit(limit: int, window: int = 60, bucket: Optional[str] = None):
    """
    Decorator for Flask routes to enforce sliding window rate limiting.
    Returns HTTP 429 Too Many Requests with Retry-After header if limit exceeded.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_rate_limit_enabled():
                return f(*args, **kwargs)

            client_ip = get_client_ip()
            b_name = bucket or request.endpoint or f.__name__
            allowed, retry_after = rate_limiter.check(client_ip, b_name, limit, window)
            if not allowed:
                resp = jsonify({
                    "error": f"Terlalu banyak permintaan. Silakan tunggu {retry_after} detik sebelum mencoba lagi.",
                    "retry_after": retry_after,
                })
                resp.status_code = 429
                resp.headers["Retry-After"] = str(retry_after)
                return resp

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def concurrent_guard(endpoint: str = "analyze"):
    """
    Decorator for Flask routes to prevent concurrent requests from the same IP.
    Returns HTTP 429 Too Many Requests if another request is still in-flight.
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_concurrent_lock_enabled():
                return f(*args, **kwargs)

            client_ip = get_client_ip()
            if not in_flight_guard.acquire(client_ip, endpoint):
                return jsonify({
                    "error": "Permintaan analisis sebelumnya sedang diproses. Harap tunggu hingga selesai."
                }), 429

            try:
                return f(*args, **kwargs)
            finally:
                in_flight_guard.release(client_ip, endpoint)
        return decorated_function
    return decorator
