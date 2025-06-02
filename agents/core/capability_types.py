from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import defaultdict
from loguru import logger

class CapabilityType(str, Enum):
    """Types of capabilities that agents can have."""
    # Existing capabilities
    DATA_PROCESSING = "data_processing"
    SENSOR_READING = "sensor_reading"
    KNOWLEDGE_GRAPH_QUERY = "knowledge_graph_query"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"
    TASK_EXECUTION = "task_execution"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    MESSAGE_PROCESSING = "message_processing"
    
    # Core coding agent capabilities
    CODE_REVIEW = "code_review"
    STATIC_ANALYSIS = "static_analysis"
    TEST_GENERATION = "test_generation"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    SECURITY_ANALYSIS = "security_analysis"
    ARCHITECTURE_REVIEW = "architecture_review"
    CODE_QUALITY = "code_quality"
    CODE_SMELL_DETECTION = "code_smell_detection"
    PATTERN_ANALYSIS = "pattern_analysis"
    
    # New capabilities for dynamic agent management
    AGENT_MANAGEMENT = "agent_management"
    WORKLOAD_MONITORING = "workload_monitoring"
    ROLE_DELEGATION = "role_delegation"
    AGENT_CREATION = "agent_creation"
    AGENT_DESTRUCTION = "agent_destruction"
    CAPABILITY_MANAGEMENT = "capability_management"
    WORKLOAD_BALANCING = "workload_balancing"
    AGENT_HEALTH_MONITORING = "agent_health_monitoring"

@dataclass
class Capability:
    """Represents a capability with type, version, and optional metadata."""
    
    def __init__(
        self,
        type: CapabilityType,
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.type = type
        self.version = version
        self.metadata = metadata or {}
        
    def __eq__(self, other):
        if not isinstance(other, Capability):
            return False
        return (
            self.type == other.type and
            self.version == other.version
        )
        
    def __hash__(self):
        return hash((self.type, self.version))
        
    def __str__(self):
        return f"{self.type.value}@{self.version}"

class CapabilitySet:
    """Thread-safe set of capabilities."""
    
    def __init__(self):
        self._capabilities: Set[Capability] = set()
        self._lock = asyncio.Lock()
        self.logger = logger.bind(component="CapabilitySet")
        
    async def add(self, capability: Capability) -> None:
        """Add a capability to the set."""
        async with self._lock:
            self._capabilities.add(capability)
            self.logger.debug(f"Added capability: {capability.type}")
            
    async def remove(self, capability: Capability) -> None:
        """Remove a capability from the set."""
        async with self._lock:
            self._capabilities.discard(capability)
            self.logger.debug(f"Removed capability: {capability.type}")
            
    async def get_all(self) -> Set[Capability]:
        """Get all capabilities in the set."""
        async with self._lock:
            return self._capabilities.copy()
            
    async def has_capability(self, capability_type: CapabilityType) -> bool:
        """Check if the set has a specific capability type."""
        async with self._lock:
            return any(c.type == capability_type for c in self._capabilities)
            
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type."""
        async with self._lock:
            for capability in self._capabilities:
                if capability.type == capability_type:
                    return capability
            return None
            
    async def clear(self) -> None:
        """Clear all capabilities from the set."""
        async with self._lock:
            self._capabilities.clear()
            self.logger.debug("Cleared all capabilities")
            
    async def update_parameters(self, capability_type: CapabilityType, parameters: Dict[str, Any]) -> None:
        """Update parameters for a specific capability."""
        async with self._lock:
            for capability in self._capabilities:
                if capability.type == capability_type:
                    capability.parameters = parameters
                    self.logger.debug(f"Updated parameters for capability: {capability_type}")
                    return
                    
    async def update_metadata(self, capability_type: CapabilityType, metadata: Dict[str, Any]) -> None:
        """Update metadata for a specific capability."""
        async with self._lock:
            for capability in self._capabilities:
                if capability.type == capability_type:
                    capability.metadata = metadata
                    self.logger.debug(f"Updated metadata for capability: {capability_type}")
                    return

    def __iter__(self):
        return iter(self._capabilities)
        
    def __len__(self):
        return len(self._capabilities)
        
    def __str__(self):
        return str(self._capabilities)

    def __eq__(self, other: Any) -> bool:
        """Compare two capability sets."""
        if not isinstance(other, CapabilitySet):
            return False
        return self._capabilities == other._capabilities
    
    def __repr__(self) -> str:
        """Get a detailed string representation of the capability set."""
        return f"CapabilitySet(capabilities={self._capabilities})" 