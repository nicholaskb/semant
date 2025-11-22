import asyncio
import time
import re
from typing import Any, Optional, Dict, List, Tuple, Set
from collections import defaultdict, Counter

class AsyncLRUCache:
    """Enhanced async-aware LRU cache with frequency-based optimizations."""

    def __init__(self, maxsize: int = 1000):
        self.cache: Dict[str, Tuple[Any, float]] = {}  # (value, expiry_time)
        self.maxsize = maxsize
        self.lock = asyncio.Lock()
        self.access_times: Dict[str, float] = {}
        self.access_counts: Counter[str] = Counter()  # Track access frequency
        self.lru = []
        self.query_patterns: Dict[str, Set[str]] = defaultdict(set)  # Pattern -> keys
        self.pattern_stats: Counter[str] = Counter()  # Pattern access counts

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache, updating access patterns."""
        async with self.lock:
            if key in self.cache:
                value, expiry_time = self.cache[key]
                if expiry_time > time.time():  # Check if not expired
                    self.access_times[key] = time.time()
                    self.access_counts[key] += 1
                    self.lru.remove(key)
                    self.lru.append(key)

                    # Update pattern stats
                    pattern = self._extract_query_pattern(key)
                    if pattern:
                        self.pattern_stats[pattern] += 1

                    return value
                else:
                    # Remove expired entry
                    await self._remove_key(key)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in the cache with intelligent eviction."""
        async with self.lock:
            expiry_time = time.time() + ttl if ttl is not None else float('inf')

            if key in self.cache:
                # Update existing entry
                self.cache[key] = (value, expiry_time)
                self.lru.remove(key)
                self.lru.append(key)
            else:
                # New entry - check if we need to evict
                if len(self.cache) >= self.maxsize:
                    await self._evict_least_valuable()
                self.cache[key] = (value, expiry_time)
                self.lru.append(key)

            self.access_times[key] = time.time()

            # Track query pattern
            pattern = self._extract_query_pattern(key)
            if pattern:
                self.query_patterns[pattern].add(key)

    async def _evict_least_valuable(self):
        """Evict the least valuable entry based on frequency and recency."""
        if not self.lru:
            return

        # Calculate value score for each entry (frequency * recency)
        current_time = time.time()
        scores = {}

        for key in self.lru:
            if key in self.access_counts and key in self.access_times:
                frequency = self.access_counts[key]
                recency = current_time - self.access_times[key]
                # Higher score = more valuable (higher frequency, more recent)
                scores[key] = frequency / (recency + 1)  # +1 to avoid division by zero
            else:
                scores[key] = 0

        # Find the key with the lowest score
        least_valuable = min(scores.items(), key=lambda x: x[1])[0]

        # Remove it
        await self._remove_key(least_valuable)

    async def _remove_key(self, key: str):
        """Remove a key from all internal structures."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
        if key in self.access_counts:
            del self.access_counts[key]
        if key in self.lru:
            self.lru.remove(key)

        # Remove from pattern tracking
        for pattern, keys in self.query_patterns.items():
            if key in keys:
                keys.remove(key)
                if not keys:
                    del self.query_patterns[pattern]
                break

    def _extract_query_pattern(self, key: str) -> Optional[str]:
        """Extract query pattern from cache key for frequency analysis."""
        if not key.startswith("query:"):
            return None

        query = key[6:]  # Remove "query:" prefix

        # Extract common SPARQL patterns
        if "SELECT" in query and "WHERE" in query:
            # Remove variable names and specific URIs to get pattern
            pattern = re.sub(r'\?\w+', '?var', query)
            pattern = re.sub(r'<[^>]+>', '<uri>', pattern)
            pattern = re.sub(r'"[^"]*"', '"value"', pattern)
            return pattern

        return None

    async def clear(self):
        """Clear all entries and reset statistics."""
        async with self.lock:
            self.cache.clear()
            self.access_times.clear()
            self.access_counts.clear()
            self.lru.clear()
            self.query_patterns.clear()
            self.pattern_stats.clear()

    async def remove(self, key: str):
        """Remove a specific key from the cache."""
        async with self.lock:
            await self._remove_key(key)

    async def keys(self) -> List[str]:
        """Get all keys in the cache."""
        async with self.lock:
            return list(self.cache.keys())

    async def warm_cache(self, common_queries: List[str], kg_manager):
        """Warm the cache with frequently used queries."""
        async with self.lock:
            for query in common_queries:
                try:
                    # Execute query to populate cache
                    await kg_manager.query_graph(query)
                except Exception:
                    # Skip queries that fail during warmup
                    continue

    async def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about query patterns."""
        async with self.lock:
            return {
                'pattern_counts': dict(self.pattern_stats),
                'total_patterns': len(self.query_patterns),
                'most_common_patterns': self.pattern_stats.most_common(10)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_accesses = sum(self.access_counts.values())
        avg_frequency = total_accesses / len(self.access_counts) if self.access_counts else 0

        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'total_accesses': total_accesses,
            'avg_access_frequency': avg_frequency,
            'unique_patterns': len(self.query_patterns),
            'most_accessed_keys': self.access_counts.most_common(5),
            'cache_utilization': len(self.cache) / self.maxsize if self.maxsize > 0 else 0
        } 