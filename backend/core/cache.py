"""Simple TTL cache for dashboard and filter queries."""
from __future__ import annotations

import threading
from cachetools import TTLCache

_lock = threading.Lock()

# Dashboard caches (TTL: 5 minutes)
_dashboard_cache: TTLCache = TTLCache(maxsize=32, ttl=300)

# Filter caches (TTL: 5 minutes)
_filter_cache: TTLCache = TTLCache(maxsize=16, ttl=300)


def get_cached(cache_name: str, key: str):
    cache = _dashboard_cache if cache_name == "dashboard" else _filter_cache
    with _lock:
        return cache.get(key)


def set_cached(cache_name: str, key: str, value):
    cache = _dashboard_cache if cache_name == "dashboard" else _filter_cache
    with _lock:
        cache[key] = value


def invalidate(cache_name: str | None = None):
    with _lock:
        if cache_name is None:
            _dashboard_cache.clear()
            _filter_cache.clear()
        elif cache_name == "dashboard":
            _dashboard_cache.clear()
        elif cache_name == "filter":
            _filter_cache.clear()
