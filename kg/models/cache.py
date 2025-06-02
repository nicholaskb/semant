import asyncio
import time
from typing import Any, Optional, Dict, List, Tuple

class AsyncLRUCache:
    """Async-aware LRU cache implementation for query results."""
    
    def __init__(self, maxsize: int = 1000):
        self.cache: Dict[str, Tuple[Any, float]] = {}  # (value, expiry_time)
        self.maxsize = maxsize
        self.lock = asyncio.Lock()
        self.access_times: Dict[str, float] = {}
        self.lru = []
        
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache, updating its access time."""
        async with self.lock:
            if key in self.cache:
                value, expiry_time = self.cache[key]
                if expiry_time > time.time():  # Check if not expired
                    self.access_times[key] = time.time()
                    self.lru.remove(key)
                    self.lru.append(key)
                    return value
                else:
                    # Remove expired entry
                    del self.cache[key]
                    del self.access_times[key]
                    self.lru.remove(key)
            return None
            
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in the cache, evicting least recently used if needed."""
        async with self.lock:
            expiry_time = time.time() + ttl if ttl is not None else float('inf')
            
            if key in self.cache:
                self.cache[key] = (value, expiry_time)
                self.lru.remove(key)
                self.lru.append(key)
            else:
                if len(self.cache) >= self.maxsize:
                    # Remove least recently used
                    oldest = self.lru.pop(0)
                    del self.cache[oldest]
                    del self.access_times[oldest]
                self.cache[key] = (value, expiry_time)
            self.access_times[key] = time.time()
            self.lru.append(key)
            
    async def clear(self):
        """Clear all entries from the cache."""
        async with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.lru.clear()
            
    async def remove(self, key: str):
        """Remove a specific key from the cache."""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                self.lru.remove(key)
                
    async def keys(self) -> List[str]:
        """Get all keys in the cache."""
        return list(self.cache.keys())
        
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': sum(1 for _ in self.cache.values()),
            'misses': sum(1 for _ in self.access_times.values()) - len(self.cache)
        } 