"""
Image Cache for Midjourney Integration
=======================================
Provides caching functionality for generated images to reduce redundant API calls.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
from loguru import logger

# Optional: Redis support for distributed caching
try:
    import redis
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.info("Redis not available, using file-based cache")


class ImageCache:
    """
    Caches generated images to avoid redundant Midjourney API calls.
    
    Supports both file-based and Redis-based caching.
    Cache keys are generated from prompt + parameters hash.
    """
    
    def __init__(
        self,
        cache_dir: str = ".cache/midjourney",
        ttl_hours: int = 24,
        max_cache_size_mb: int = 500,
        redis_url: Optional[str] = None
    ):
        """
        Initialize the image cache.
        
        Args:
            cache_dir: Directory for file-based cache
            ttl_hours: Time-to-live for cache entries in hours
            max_cache_size_mb: Maximum cache size in MB
            redis_url: Optional Redis URL for distributed caching
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # Convert to bytes
        self.redis_client = None
        
        # Initialize Redis if available and URL provided
        if REDIS_AVAILABLE and redis_url:
            asyncio.create_task(self._init_redis(redis_url))
        
        # Create cache metadata file
        self.metadata_file = self.cache_dir / "metadata.json"
        self.metadata = self._load_metadata()
        
        logger.info(f"ImageCache initialized: dir={cache_dir}, ttl={ttl_hours}h, max={max_cache_size_mb}MB")
    
    async def _init_redis(self, redis_url: str):
        """Initialize Redis connection."""
        try:
            self.redis_client = await aioredis.from_url(redis_url)
            await self.redis_client.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, falling back to file cache")
            self.redis_client = None
    
    def _generate_cache_key(self, prompt: str, **params) -> str:
        """
        Generate a unique cache key from prompt and parameters.
        
        Args:
            prompt: The generation prompt
            **params: Additional parameters (version, aspect_ratio, etc.)
            
        Returns:
            SHA256 hash of the combined inputs
        """
        # Sort parameters for consistent hashing
        cache_data = {
            "prompt": prompt.strip().lower(),
            "version": params.get("version", "v6"),
            "aspect_ratio": params.get("aspect_ratio", "1:1"),
            "process_mode": params.get("process_mode", "relax"),
            "cref": params.get("cref"),
            "cw": params.get("cw"),
            "oref": params.get("oref"),
            "ow": params.get("ow"),
        }
        
        # Remove None values
        cache_data = {k: v for k, v in cache_data.items() if v is not None}
        
        # Create hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    async def get(self, prompt: str, **params) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached image data if available and not expired.
        
        Args:
            prompt: The generation prompt
            **params: Additional parameters
            
        Returns:
            Cached data dict or None if not found/expired
        """
        cache_key = self._generate_cache_key(prompt, **params)
        
        # Try Redis first if available
        if self.redis_client:
            try:
                data = await self.redis_client.get(f"midjourney:{cache_key}")
                if data:
                    cached = json.loads(data)
                    if self._is_valid(cached):
                        logger.info(f"Cache hit (Redis): {cache_key[:8]}...")
                        return cached
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fall back to file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                
                if self._is_valid(cached):
                    logger.info(f"Cache hit (file): {cache_key[:8]}...")
                    return cached
                else:
                    # Remove expired entry
                    cache_file.unlink()
                    self._update_metadata_remove(cache_key)
            except Exception as e:
                logger.error(f"Error reading cache file: {e}")
        
        logger.debug(f"Cache miss: {cache_key[:8]}...")
        return None
    
    async def set(
        self,
        prompt: str,
        result: Dict[str, Any],
        **params
    ) -> bool:
        """
        Store image generation result in cache.
        
        Args:
            prompt: The generation prompt
            result: Generation result containing image URL, task_id, etc.
            **params: Additional parameters used for generation
            
        Returns:
            True if cached successfully
        """
        cache_key = self._generate_cache_key(prompt, **params)
        
        # Prepare cache entry
        cache_entry = {
            "prompt": prompt,
            "params": params,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "expires": (datetime.now() + self.ttl).isoformat()
        }
        
        # Store in Redis if available
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"midjourney:{cache_key}",
                    int(self.ttl.total_seconds()),
                    json.dumps(cache_entry)
                )
                logger.debug(f"Cached to Redis: {cache_key[:8]}...")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        # Store in file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_entry, f, indent=2)
            
            # Update metadata
            self._update_metadata_add(cache_key, len(json.dumps(cache_entry)))
            
            # Check cache size and cleanup if needed
            await self._cleanup_if_needed()
            
            logger.debug(f"Cached to file: {cache_key[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error writing cache file: {e}")
            return False
    
    def _is_valid(self, cached: Dict[str, Any]) -> bool:
        """Check if cached entry is still valid (not expired)."""
        try:
            expires = datetime.fromisoformat(cached["expires"])
            return datetime.now() < expires
        except:
            return False
    
    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "entries": {},
            "total_size": 0,
            "last_cleanup": datetime.now().isoformat()
        }
    
    def _save_metadata(self):
        """Save cache metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
    
    def _update_metadata_add(self, cache_key: str, size: int):
        """Update metadata when adding cache entry."""
        self.metadata["entries"][cache_key] = {
            "size": size,
            "timestamp": datetime.now().isoformat()
        }
        self.metadata["total_size"] = sum(
            e["size"] for e in self.metadata["entries"].values()
        )
        self._save_metadata()
    
    def _update_metadata_remove(self, cache_key: str):
        """Update metadata when removing cache entry."""
        if cache_key in self.metadata["entries"]:
            del self.metadata["entries"][cache_key]
            self.metadata["total_size"] = sum(
                e["size"] for e in self.metadata["entries"].values()
            )
            self._save_metadata()
    
    async def _cleanup_if_needed(self):
        """Remove old entries if cache size exceeds limit."""
        if self.metadata["total_size"] > self.max_cache_size:
            logger.info("Cache size exceeded, cleaning up...")
            
            # Sort entries by timestamp (oldest first)
            entries = sorted(
                self.metadata["entries"].items(),
                key=lambda x: x[1]["timestamp"]
            )
            
            # Remove oldest entries until under limit
            removed = 0
            for cache_key, entry in entries:
                if self.metadata["total_size"] <= self.max_cache_size * 0.8:  # 80% threshold
                    break
                
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    cache_file.unlink()
                    removed += 1
                
                self._update_metadata_remove(cache_key)
            
            logger.info(f"Removed {removed} old cache entries")
            self.metadata["last_cleanup"] = datetime.now().isoformat()
    
    async def clear(self):
        """Clear all cache entries."""
        logger.info("Clearing image cache...")
        
        # Clear Redis if available
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("midjourney:*")
                if keys:
                    await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis cache entries")
            except Exception as e:
                logger.error(f"Error clearing Redis cache: {e}")
        
        # Clear file cache
        removed = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name != "metadata.json":
                cache_file.unlink()
                removed += 1
        
        # Reset metadata
        self.metadata = {
            "entries": {},
            "total_size": 0,
            "last_cleanup": datetime.now().isoformat()
        }
        self._save_metadata()
        
        logger.info(f"Cleared {removed} file cache entries")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "total_entries": len(self.metadata["entries"]),
            "total_size_mb": self.metadata["total_size"] / (1024 * 1024),
            "max_size_mb": self.max_cache_size / (1024 * 1024),
            "usage_percent": (self.metadata["total_size"] / self.max_cache_size * 100) if self.max_cache_size else 0,
            "last_cleanup": self.metadata.get("last_cleanup"),
            "ttl_hours": self.ttl.total_seconds() / 3600,
            "redis_connected": self.redis_client is not None
        }
        
        # Get Redis stats if available
        if self.redis_client:
            try:
                keys = await self.redis_client.keys("midjourney:*")
                stats["redis_entries"] = len(keys)
            except:
                stats["redis_entries"] = 0
        
        return stats
    
    async def close(self):
        """Close cache connections."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis cache connection closed")


# Global cache instance
_cache_instance: Optional[ImageCache] = None


def get_cache() -> Optional[ImageCache]:
    """Get the global cache instance."""
    return _cache_instance


async def initialize_cache(
    cache_dir: str = ".cache/midjourney",
    ttl_hours: int = 24,
    max_cache_size_mb: int = 500,
    redis_url: Optional[str] = None
) -> ImageCache:
    """
    Initialize the global cache instance.
    
    Args:
        cache_dir: Directory for file-based cache
        ttl_hours: Time-to-live for cache entries
        max_cache_size_mb: Maximum cache size in MB
        redis_url: Optional Redis URL
        
    Returns:
        Initialized ImageCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = ImageCache(
            cache_dir=cache_dir,
            ttl_hours=ttl_hours,
            max_cache_size_mb=max_cache_size_mb,
            redis_url=redis_url
        )
    
    return _cache_instance
