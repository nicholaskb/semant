from typing import Dict, Set, Tuple, Any
from rdflib import RDF
import asyncio
import time

class TripleIndex:
    """Efficient indexing for triple patterns with thread safety and TTL-based cleanup."""
    
    def __init__(self, ttl: int = 3600):  # Default TTL of 1 hour
        # Index by predicate
        self.predicate_index: Dict[str, Set[Tuple[str, str]]] = {}
        # Index by type
        self.type_index: Dict[str, Set[str]] = {}
        # Index by relationship
        self.relationship_index: Dict[str, Dict[str, Set[str]]] = {}
        # TTL tracking
        self._last_cleanup = time.time()
        self._ttl = ttl
        self._lock = asyncio.Lock()
        self._stats_cache = None
        self._stats_timestamp = 0
        self._stats_ttl = 60  # Stats cache TTL of 60 seconds
        
    async def _cleanup_expired(self) -> None:
        """Clean up expired entries based on TTL."""
        current_time = time.time()
        if current_time - self._last_cleanup > self._ttl:
            async with self._lock:
                # Reset indices
                self.predicate_index.clear()
                self.type_index.clear()
                self.relationship_index.clear()
                self._last_cleanup = current_time
                self._stats_cache = None
        
    async def index_triple(self, subject: str, predicate: str, object: str):
        """Index a triple using multiple indexing strategies."""
        await self._cleanup_expired()
        
        async with self._lock:
            # Index by predicate
            if predicate not in self.predicate_index:
                self.predicate_index[predicate] = set()
            self.predicate_index[predicate].add((subject, object))
            
            # Index by type
            if predicate == str(RDF.type):
                if object not in self.type_index:
                    self.type_index[object] = set()
                self.type_index[object].add(subject)
                
            # Index by relationship
            if predicate not in self.relationship_index:
                self.relationship_index[predicate] = {}
            if object not in self.relationship_index[predicate]:
                self.relationship_index[predicate][object] = set()
            self.relationship_index[predicate][object].add(subject)
            
            # Invalidate stats cache
            self._stats_cache = None
        
    async def get_by_predicate(self, predicate: str) -> Set[Tuple[str, str]]:
        """Get all (subject, object) pairs for a predicate."""
        await self._cleanup_expired()
        async with self._lock:
            return self.predicate_index.get(predicate, set()).copy()
        
    async def get_by_type(self, type_uri: str) -> Set[str]:
        """Get all subjects of a specific type."""
        await self._cleanup_expired()
        async with self._lock:
            return self.type_index.get(type_uri, set()).copy()
        
    async def get_by_relationship(self, predicate: str, object: str) -> Set[str]:
        """Get all subjects related to an object through a predicate."""
        await self._cleanup_expired()
        async with self._lock:
            return self.relationship_index.get(predicate, {}).get(object, set()).copy()
        
    async def clear(self):
        """Clear all indices."""
        async with self._lock:
            self.predicate_index.clear()
            self.type_index.clear()
            self.relationship_index.clear()
            self._stats_cache = None
            self._last_cleanup = time.time()
        
    async def get_stats(self) -> Dict[str, int]:
        """Get index statistics with caching."""
        await self._cleanup_expired()
        
        current_time = time.time()
        if self._stats_cache is not None and current_time - self._stats_timestamp < self._stats_ttl:
            return self._stats_cache.copy()
            
        async with self._lock:
            stats = {
                'predicate_count': len(self.predicate_index),
                'type_count': len(self.type_index),
                'relationship_count': len(self.relationship_index),
                'total_triples': sum(len(pairs) for pairs in self.predicate_index.values())
            }
            self._stats_cache = stats.copy()
            self._stats_timestamp = current_time
            return stats 