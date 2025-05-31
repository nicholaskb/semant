from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import defaultdict

class CapabilityType(Enum):
    """Standardized capability types."""
    RESEARCH = "research"
    DATA_PROCESSING = "data_processing"
    SENSOR_DATA = "sensor_data"
    FEATURE_PROCESSING = "feature_processing"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    REASONING = "reasoning"
    VALIDATION = "validation"

@dataclass
class Capability:
    """Standardized capability representation."""
    type: CapabilityType
    version: str
    metadata: Dict[str, Any] = None

    def __hash__(self):
        return hash((self.type, self.version))

    def __eq__(self, other):
        if not isinstance(other, Capability):
            return False
        return self.type == other.type and self.version == other.version

class CapabilitySet:
    """Thread-safe capability set implementation."""
    def __init__(self):
        self._capabilities: Set[Capability] = set()
        self._lock = asyncio.Lock()
    
    async def add(self, capability: Capability) -> None:
        async with self._lock:
            self._capabilities.add(capability)
    
    async def remove(self, capability: Capability) -> None:
        async with self._lock:
            self._capabilities.discard(capability)
    
    async def get_all(self) -> Set[Capability]:
        async with self._lock:
            return self._capabilities.copy()
    
    async def has_capability(self, capability_type: CapabilityType) -> bool:
        async with self._lock:
            return any(c.type == capability_type for c in self._capabilities)
    
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        async with self._lock:
            for capability in self._capabilities:
                if capability.type == capability_type:
                    return capability
            return None 