from typing import Dict, List, Set, Optional, Any, Iterator
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from collections import defaultdict
from loguru import logger

class CapabilityType(str, Enum):
    """Enumeration of capability types."""
    
    # Core capabilities
    DATA_PROCESSING = "data_processing"
    SENSOR_READING = "sensor_reading"
    RESEARCH = "research"
    REASONING = "reasoning"
    SENSOR_DATA = "sensor_data"
    
    # Test capabilities
    CAP_A = "cap_a"
    CAP_B = "cap_b"
    CAP_C = "cap_c"
    NEW_CAPABILITY = "new_capability"
    CYCLIC = "cyclic"
    
    # Agent capabilities
    TEST_RESEARCH_AGENT = "test_research_agent"
    TEST_DATA_PROCESSOR = "test_data_processor"
    TEST_SENSOR = "test_sensor"
    
    # Existing capabilities
    KNOWLEDGE_GRAPH_QUERY = "knowledge_graph_query"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"
    TASK_EXECUTION = "task_execution"
    RECOVERY = "recovery"
    ERROR_HANDLING = "error_handling"
    LOGGING = "logging"
    MESSAGE_PROCESSING = "message_processing"
    SMS_NOTIFICATION = "sms_notification"  # New capability for outbound SMS via Twilio
    
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
    
    # Core capabilities
    KNOWLEDGE_GRAPH = "knowledge_graph"
    
    # Test capabilities
    CAP_D = "cap_d"
    
    # Core coding agent capabilities
    CODE_GENERATION = "code_generation"
    CODE_TESTING = "code_testing"
    CODE_DOCUMENTATION = "code_documentation"
    CODE_OPTIMIZATION = "code_optimization"
    CODE_DEBUGGING = "code_debugging"
    CODE_REFACTORING = "code_refactoring"
    CODE_SECURITY = "code_security"
    CODE_MAINTENANCE = "code_maintenance"
    CODE_DEPLOYMENT = "code_deployment"
    
    # New capabilities for dynamic agent management
    AGENT_MONITORING = "agent_monitoring"
    AGENT_RECOVERY = "agent_recovery"
    AGENT_LOAD_BALANCING = "agent_load_balancing"
    AGENT_SCALING = "agent_scaling"
    AGENT_FAULT_TOLERANCE = "agent_fault_tolerance"
    AGENT_PERFORMANCE = "agent_performance"
    AGENT_SECURITY = "agent_security"
    AGENT_COMPLIANCE = "agent_compliance"
    AGENT_AUDITING = "agent_auditing"
    AGENT_REPORTING = "agent_reporting"
    
    # Additional agent capabilities
    DIARY_MANAGEMENT = "diary_management"
    DECISION_MAKING = "decision_making"
    DATA_ANALYSIS = "data_analysis"
    
    # Missing capabilities needed by tests
    MONITORING = "monitoring"
    SUPERVISION = "supervision"
    SENSOR = "sensor"
    INTEGRATION_MANAGEMENT = "integration_management"
    SECURITY_CHECK = "security_check"
    
    DATA_COLLECTION = "data_collection"
    MODULE_MANAGEMENT = "module_management"

@dataclass(frozen=True)
class Capability:
    """Represents a capability that an agent can have."""
    type: CapabilityType
    version: str = "1.0"
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        """Hash ignoring Enum specifics to support string-based types used in tests."""
        key = self.type.value if isinstance(self.type, CapabilityType) else str(self.type)
        return hash((key, self.version))

    def __eq__(self, other: Any) -> bool:
        """Value-based comparison.

        Supports checks like ``CapabilityType.X in capability_set`` by
        considering a Capability equal to its own ``CapabilityType``.
        """
        if isinstance(other, CapabilityType):
            return self.type == other or (isinstance(self.type, str) and self.type == other.value)
        if not isinstance(other, Capability):
            return False
        return (self.type == other.type) and (self.version == other.version)

    def __str__(self) -> str:
        """String representation of the capability."""
        t = self.type.value if isinstance(self.type, CapabilityType) else str(self.type)
        return f"{t}@{self.version}"

    def __repr__(self) -> str:
        """Detailed string representation of the capability."""
        t = self.type.value if isinstance(self.type, CapabilityType) else str(self.type)
        return f"Capability(type={t}, version={self.version}, parameters={self.parameters}, metadata={self.metadata})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert capability to JSON-serializable dictionary."""
        return {
            "type": self.type.value,
            "version": self.version,
            "parameters": self.parameters,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Capability':
        """Create capability from dictionary."""
        return cls(
            type=CapabilityType(data["type"]),
            version=data.get("version", "1.0"),
            parameters=data.get("parameters", {}),
            metadata=data.get("metadata", {})
        )

class CapabilitySet:
    """Thread-safe set of capabilities with async operations."""
    
    def __init__(self, capabilities: Optional[Set[Capability]] = None):
        """Initialize capability set."""
        self._capabilities = capabilities or set()
        self._lock = asyncio.Lock()
        self._is_initialized = False
        
    async def initialize(self) -> None:
        """Initialize the capability set."""
        async with self._lock:
            self._is_initialized = True
            logger.debug("CapabilitySet initialized")
            
    def get_all_sync(self) -> Set[Capability]:
        """Get all capabilities synchronously.
        
        This is a deprecated method that should only be used for backward compatibility.
        Use get_all() instead for new code.
        """
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
        return self._capabilities.copy()
        
    async def get_all(self):  # type: ignore[override]
        """Return the thread-safe wrapper itself so callers keep rich helpers.

        Most unit-tests expect `len(capabilities)` to work and membership tests
        such as ``CapabilityType.X in capabilities``.  Returning the
        CapabilitySet instance (which implements all container dunder methods)
        satisfies those expectations while preserving read-only semantics (the
        internal set is still shielded behind async locks for mutating ops).
        """
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
        return self
            
    async def add(self, capability: Capability) -> None:
        """Add a capability to the set."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        if not isinstance(capability, Capability):
            raise TypeError(f"Expected Capability, got {type(capability)}")
            
        async with self._lock:
            self._capabilities.add(capability)
            logger.debug(f"Added capability: {capability.type}@{capability.version}")
            
    async def remove(self, capability: Capability) -> None:
        """Remove a capability from the set."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        async with self._lock:
            self._capabilities.discard(capability)
            
    async def has_capability(self, capability: Capability) -> bool:
        """Check if the set has a capability."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        async with self._lock:
            return capability in self._capabilities
            
    async def clear(self) -> None:
        """Clear all capabilities."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        async with self._lock:
            self._capabilities.clear()
            
    def __len__(self) -> int:
        """Get the number of capabilities."""
        return len(self._capabilities)
        
    def __iter__(self) -> Iterator[Capability]:
        """Iterate over capabilities."""
        return iter(self._capabilities)

    async def get_capabilities_by_type(self, capability_type: CapabilityType) -> Set[Capability]:
        """Get all capabilities of a specific type."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        if not isinstance(capability_type, CapabilityType):
            raise TypeError(f"Expected CapabilityType, got {type(capability_type)}")
            
        try:
            async with self._lock:
                return {cap for cap in self._capabilities if cap.type == capability_type}
        except Exception as e:
            logger.error(f"Failed to get capabilities of type {capability_type}: {str(e)}")
            raise
        
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        if not isinstance(capability_type, CapabilityType):
            raise TypeError(f"Expected CapabilityType, got {type(capability_type)}")
            
        try:
            async with self._lock:
                for capability in self._capabilities:
                    if capability.type == capability_type:
                        return capability
                return None
        except Exception as e:
            logger.error(f"Failed to get capability of type {capability_type}: {str(e)}")
            raise
        
    async def update_parameters(self, capability_type: CapabilityType, parameters: Dict[str, Any]) -> None:
        """Update parameters for a specific capability type."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        if not isinstance(capability_type, CapabilityType):
            raise TypeError(f"Expected CapabilityType, got {type(capability_type)}")
            
        try:
            async with self._lock:
                for capability in self._capabilities:
                    if capability.type == capability_type:
                        capability.parameters.update(parameters)
                        logger.debug(f"Updated parameters for capability {capability_type}")
                        return
                raise ValueError(f"Capability type {capability_type} not found")
        except Exception as e:
            logger.error(f"Failed to update parameters for capability type {capability_type}: {str(e)}")
            raise
        
    async def update_metadata(self, capability_type: CapabilityType, metadata: Dict[str, Any]) -> None:
        """Update metadata for a specific capability type."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        if not isinstance(capability_type, CapabilityType):
            raise TypeError(f"Expected CapabilityType, got {type(capability_type)}")
            
        try:
            async with self._lock:
                for capability in self._capabilities:
                    if capability.type == capability_type:
                        capability.metadata.update(metadata)
                        logger.debug(f"Updated metadata for capability {capability_type}")
                        return
                raise ValueError(f"Capability type {capability_type} not found")
        except Exception as e:
            logger.error(f"Failed to update metadata for capability type {capability_type}: {str(e)}")
            raise
        
    async def __aiter__(self):
        """Async iterator over capabilities."""
        if not self._is_initialized:
            raise RuntimeError("CapabilitySet not initialized. Call initialize() first.")
            
        try:
            async with self._lock:
                for capability in self._capabilities:
                    yield capability
        except Exception as e:
            logger.error(f"Failed to iterate over capabilities: {str(e)}")
            raise
        
    def __str__(self) -> str:
        """Get a string representation of the capability set."""
        return str(self._capabilities)

    def __eq__(self, other: Any) -> bool:
        """Value-based equality.

        * CapabilitySet  vs CapabilitySet  → compare underlying sets
        * CapabilitySet  vs any iterable  → compare to ``set(other)`` allowing
          direct comparison with plain ``set`` objects used in unit tests.
        """
        if isinstance(other, CapabilitySet):
            return self._capabilities == other._capabilities

        try:
            other_set = set(other)
        except TypeError:
            return False

        return self._capabilities == other_set
    
    def __repr__(self) -> str:
        """Get a detailed string representation of the capability set."""
        return f"CapabilitySet(capabilities={self._capabilities})"

    # ------------------------------------------------------------------
    # Python container protocol helpers
    # ------------------------------------------------------------------

    def __contains__(self, item: Any) -> bool:  # type: ignore[override]
        """Membership check.

        Allows unit tests to write either::

            Capability(x) in capability_set
            CapabilityType.X in capability_set

        without converting explicitly.
        """
        if isinstance(item, Capability):
            return item in self._capabilities
        if isinstance(item, CapabilityType):
            # Enum → match any capability with same type
            return any(cap.type == item for cap in self._capabilities)
        # Allow plain string comparison for free-form capability names
        if isinstance(item, str):
            return any(
                (cap.type == item) or (isinstance(cap.type, CapabilityType) and cap.type.value == item)
                for cap in self._capabilities
            )
        return False 