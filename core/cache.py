import time
import threading
from typing import Optional, Any, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class MemoryCache:
    """
    High-performance In-Memory Cache with TTL support.
    Replaces Redis for environments with limited resources.
    Thread-safe and persistent within the application process.
    """
    _instance: Optional['MemoryCache'] = None
    _lock = threading.Lock()

    def __init__(self):
        # Storage format: {key: (value, expire_at)}
        self._cache: Dict[str, Tuple[Any, float]] = {}
        logger.info("Initialized In-Memory Cache")

    @classmethod
    def get_instance(cls) -> 'MemoryCache':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get(self, key: str) -> Optional[str]:
        """Get value from cache if not expired"""
        with self._lock:
            data = self._cache.get(key)
            if not data:
                return None
            
            value, expire_at = data
            
            # Check if expired
            if expire_at and time.time() > expire_at:
                del self._cache[key]
                return None
                
            return value

    def set(self, key: str, value: Any, ex: Optional[int] = None, **kwargs) -> bool:
        """Set value in cache with optional TTL (seconds)"""
        expire_at = time.time() + ex if ex else None
        
        with self._lock:
            self._cache[key] = (value, expire_at)
        return True

    def setex(self, key: str, time_seconds: int, value: Any) -> bool:
        """Set value with explicit TTL"""
        return self.set(key, value, ex=time_seconds)

    def delete(self, key: str) -> int:
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return 1
            return 0

    def flush_all(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()

    def is_alive(self) -> bool:
        return True

def get_cache() -> MemoryCache:
    return MemoryCache.get_instance()
