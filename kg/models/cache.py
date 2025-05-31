import asyncio
import time
from typing import Any, Optional, Dict

class AsyncLRUCache:
    """Async-aware LRU cache implementation for query results."""
    
    def __init__(self, maxsize: int = 1000):
        self.cache: Dict[str, Any] = {}
        self.maxsize = maxsize
        self.lock = asyncio.Lock()
        self.access_times: Dict[str, float] = {}
        
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache, updating its access time."""
        async with self.lock:
            if key in self.cache:
                self.access_times[key] = time.time()
                return self.cache[key]
            return None
            
    async def set(self, key: str, value: Any):
        """Set a value in the cache, evicting least recently used if needed."""
        async with self.lock:
            if len(self.cache) >= self.maxsize:
                # Remove least recently used
                lru_key = min(self.access_times.items(), key=lambda x: x[1])[0]
                del self.cache[lru_key]
                del self.access_times[lru_key]
            self.cache[key] = value
            self.access_times[key] = time.time()
            
    async def clear(self):
        """Clear all entries from the cache."""
        async with self.lock:
            self.cache.clear()
            self.access_times.clear()
            
    async def remove(self, key: str):
        """Remove a specific key from the cache."""
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': sum(1 for _ in self.cache.values()),
            'misses': sum(1 for _ in self.access_times.values()) - len(self.cache)
        } 