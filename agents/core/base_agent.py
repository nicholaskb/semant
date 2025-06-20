from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Union
from pydantic import BaseModel
from loguru import logger
import time
from rdflib import BNode, Literal, URIRef
from rdflib.namespace import RDF
from rdflib import Namespace
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet

DM = Namespace("http://example.org/demo/")

class AgentStatus(str, Enum):
    """Status of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    ACTIVE = "active"

class AgentMessage:
    """Represents a message between agents."""
    
    def __init__(
        self,
        sender_id: str,
        recipient_id: str,
        content: Any,
        timestamp: Optional[Union[float, datetime]] = None,
        message_type: str = "message",
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.message_id = message_id or str(uuid.uuid4())
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.content = content
        self.timestamp = timestamp if isinstance(timestamp, datetime) else datetime.fromtimestamp(timestamp or time.time())
        self.message_type = message_type
        self.metadata = metadata or {}
        
        # Backward compatibility attributes
        self.id = self.message_id
        self.sender = sender_id
        self.recipient = recipient_id

    # ------------------------------------------------------------------
    # Dict-like helpers for backward-compatibility with legacy tests
    # ------------------------------------------------------------------
    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __iter__(self):
        # Iterate over attribute names similar to dict keys
        return iter(self.__dict__)

    def keys(self):  # type: ignore[override]
        return self.__dict__.keys()

    def items(self):  # type: ignore[override]
        return self.__dict__.items()

    def values(self):  # type: ignore[override]
        return self.__dict__.values()

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "base",
        capabilities: Optional[Set[Capability]] = None,
        knowledge_graph: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        if not agent_id:
            raise ValueError("agent_id cannot be None or empty")
            
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._capabilities = CapabilitySet()

        # ------------------------------------------------------------------
        # Legacy-compatibility: accept capability strings or CapabilityType
        # enums passed by older agent classes / tests and convert them into
        # canonical Capability objects.  This keeps new strict typing while
        # allowing existing code to run unchanged.
        # ------------------------------------------------------------------
        normalized_caps = set()
        if capabilities:
            for cap in capabilities:
                if isinstance(cap, Capability):
                    normalized_caps.add(cap)
                elif isinstance(cap, CapabilityType):
                    normalized_caps.add(Capability(cap))
                elif isinstance(cap, str):
                    try:
                        enum_val = CapabilityType(cap)
                        normalized_caps.add(Capability(enum_val))
                    except ValueError:
                        # Unknown string – skip to avoid hard crash
                        self.logger.warning(
                            f"Ignoring unknown capability string '{cap}' on agent {agent_id}"
                        )
                else:
                    self.logger.warning(
                        f"Unsupported capability type {type(cap)} on agent {agent_id} – ignored"
                    )
        self._initial_capabilities = normalized_caps
        self.knowledge_graph = knowledge_graph
        self.config: Dict[str, Any] = config or {}
        self.logger = logger.bind(agent_id=agent_id, agent_type=agent_type)
        self.message_history: List[AgentMessage] = []
        self.status = AgentStatus.IDLE
        self._status_lock = asyncio.Lock()  # Lock for status updates
        self._kg_lock = asyncio.Lock()      # Lock for knowledge graph operations
        self._capability_lock = asyncio.Lock()  # Lock for capability operations
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        if self._is_initialized:
            return
            
        async with self._initialization_lock:
            if self._is_initialized:  # Double-check after acquiring lock
                return
                
            try:
                # Initialize capabilities set first
                await self._capabilities.initialize()
                
                # Initialize capabilities
                for capability in self._initial_capabilities:
                    await self._capabilities.add(capability)
                self._initial_capabilities = set()  # Clear initial capabilities after initialization
                
                # Initialize knowledge graph if provided
                if self.knowledge_graph and hasattr(self.knowledge_graph, 'initialize'):
                    await self.knowledge_graph.initialize()
                
                self._is_initialized = True
                self.logger.debug(f"Initialized agent {self.agent_id} with capabilities: {await self.get_capabilities()}")
            except Exception as e:
                self.logger.error(f"Failed to initialize agent {self.agent_id}: {str(e)}")
                self._is_initialized = False
                raise
                
    async def get_capabilities(self) -> Set[Capability]:
        """Get the agent's capabilities.
        
        Returns:
            Set[Capability]: The set of capabilities this agent has.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get capabilities for agent {self.agent_id}: {str(e)}")
            raise
            
    async def add_capability(self, capability: Capability) -> None:
        """Add a capability to the agent.
        
        Args:
            capability: The capability to add.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                await self._capabilities.add(capability)
                self.logger.debug(f"Added capability {capability} to agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to add capability {capability} to agent {self.agent_id}: {str(e)}")
            raise
            
    async def remove_capability(self, capability: Capability) -> None:
        """Remove a capability from the agent.
        
        Args:
            capability: The capability to remove.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                await self._capabilities.remove(capability)
                self.logger.debug(f"Removed capability {capability} from agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to remove capability {capability} from agent {self.agent_id}: {str(e)}")
            raise
            
    async def has_capability(self, capability: Union[Capability, CapabilityType]) -> bool:
        """Check if the agent has a specific capability.
        
        Args:
            capability: Either a Capability object or a CapabilityType enum value.
            
        Returns:
            bool: True if the agent has the capability, False otherwise.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If the capability argument is not a Capability or CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                if isinstance(capability, CapabilityType):
                    # Convert CapabilityType to Capability for checking
                    capability = Capability(capability)
                elif not isinstance(capability, Capability):
                    raise TypeError(f"Expected Capability or CapabilityType, got {type(capability)}")
                    
                return await self._capabilities.has_capability(capability)
        except Exception as e:
            self.logger.error(f"Failed to check capability {capability} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type.
        
        Args:
            capability_type: The type of capability to get.
            
        Returns:
            Optional[Capability]: The capability if found, None otherwise.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If capability_type is not a CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_capability(capability_type)
        except Exception as e:
            self.logger.error(f"Failed to get capability of type {capability_type} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_capabilities_by_type(self, capability_type: CapabilityType) -> Set[Capability]:
        """Get all capabilities of a specific type.
        
        Args:
            capability_type: The type of capabilities to get.
            
        Returns:
            Set[Capability]: Set of capabilities of the specified type.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If capability_type is not a CapabilityType.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return await self._capabilities.get_capabilities_by_type(capability_type)
        except Exception as e:
            self.logger.error(f"Failed to get capabilities of type {capability_type} for agent {self.agent_id}: {str(e)}")
            raise
            
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a response.
        
        Args:
            message: The message to process.
            
        Returns:
            AgentMessage: The response message.
            
        Raises:
            RuntimeError: If the agent is not initialized.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                # Add message to history
                self.message_history.append(message)
                
                # Update status
                self.status = AgentStatus.BUSY
                
                # Process message
                response = await self._process_message_impl(message)
                
                # Update status
                self.status = AgentStatus.IDLE
                
                return response
        except Exception as e:
            self.logger.error(f"Failed to process message for agent {self.agent_id}: {str(e)}")
            self.status = AgentStatus.ERROR
            raise
            
    @abstractmethod
    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        """Implementation of message processing.
        
        Args:
            message: The message to process.
            
        Returns:
            AgentMessage: The response message.
        """
        pass
        
    async def update_status(self, status: AgentStatus) -> None:
        """Update the agent's status.
        
        Args:
            status: The new status to set.
            
        Raises:
            RuntimeError: If the agent is not initialized.
            TypeError: If status is not an AgentStatus.
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if not isinstance(status, AgentStatus):
            raise TypeError(f"Expected AgentStatus, got {type(status)}")
            
        try:
            async with self._status_lock:
                old_status = self.status
                self.status = status
                self.logger.debug(f"Updated agent {self.agent_id} status from {old_status} to {status}")
                
                # Update knowledge graph with new status
                if self.knowledge_graph:
                    async with self._kg_lock:
                        await self.knowledge_graph.add_triple(
                            self.agent_uri(),
                            "http://example.org/agent/hasStatus",
                            f"http://example.org/agent/{status.value}"
                        )
        except Exception as e:
            self.logger.error(f"Failed to update status for agent {self.agent_id}: {str(e)}")
            raise
            
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent.
        
        Returns:
            Dict[str, Any]: The agent's status including:
                - status: str - Current status
                - capabilities: Set[Capability] - Current capabilities
                - message_count: int - Number of messages processed
                - last_message_time: Optional[datetime] - Time of last message
        """
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        try:
            async with self._capability_lock:
                return {
                    "status": self.status,
                    "capabilities": await self.get_capabilities(),
                    "message_count": len(self.message_history),
                    "last_message_time": self.message_history[-1].timestamp if self.message_history else None
                }
        except Exception as e:
            self.logger.error(f"Failed to get status for agent {self.agent_id}: {str(e)}")
            raise
            
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        try:
            async with self._capability_lock:
                if self._is_initialized:
                    # Clean up knowledge graph if needed
                    if self.knowledge_graph and hasattr(self.knowledge_graph, 'cleanup'):
                        await self.knowledge_graph.cleanup()
                        
                    # Clear message history
                    self.message_history.clear()
                    
                    # Reset status
                    self.status = AgentStatus.OFFLINE
                    
                    self._is_initialized = False
                    self.logger.info(f"Cleaned up agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to clean up agent {self.agent_id}: {str(e)}")
            raise
            
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        try:
            await self.cleanup()
            self.logger.info(f"Shut down agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to shut down agent {self.agent_id}: {str(e)}")
            raise
            
    def agent_uri(self) -> str:
        """Get the agent's URI.
        
        Returns:
            str: The agent's URI.
        """
        return f"http://example.org/agent/{self.agent_id}"
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if not self.knowledge_graph:
            raise RuntimeError("Knowledge graph not available")
            
        try:
            async with self._kg_lock:
                if hasattr(self.knowledge_graph, 'add_triple'):
                    # Handle triple-based updates
                    for subject, predicates in update_data.items():
                        for predicate, obj in predicates.items():
                            await self.knowledge_graph.add_triple(subject, predicate, str(obj))
                else:
                    # Handle direct graph updates
                    for subject, predicates in update_data.items():
                        subject_uri = URIRef(subject)
                        for predicate, obj in predicates.items():
                            predicate_uri = URIRef(predicate)
                            if isinstance(obj, (str, int, float, bool)):
                                obj_uri = Literal(obj)
                            else:
                                obj_uri = URIRef(str(obj))
                            self.knowledge_graph.add((subject_uri, predicate_uri, obj_uri))
                            
                self.logger.debug(f"Updated knowledge graph for agent {self.agent_id}")
        except Exception as e:
            self.logger.error(f"Failed to update knowledge graph for agent {self.agent_id}: {str(e)}")
            raise
            
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for information."""
        if not self._is_initialized:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
            
        if not self.knowledge_graph:
            raise RuntimeError("Knowledge graph not available")
            
        try:
            async with self._kg_lock:
                if hasattr(self.knowledge_graph, 'query'):
                    # Handle SPARQL queries
                    if "sparql" in query:
                        results = await self.knowledge_graph.query(query["sparql"])
                        return {"results": results}
                    else:
                        raise ValueError("SPARQL query required")
                else:
                    # Handle direct graph queries
                    if "subject" in query:
                        subject = URIRef(query["subject"])
                        if "predicate" in query:
                            predicate = URIRef(query["predicate"])
                            if "object" in query:
                                obj = URIRef(query["object"])
                                results = list(self.knowledge_graph.triples((subject, predicate, obj)))
                            else:
                                results = list(self.knowledge_graph.triples((subject, predicate, None)))
                        else:
                            results = list(self.knowledge_graph.triples((subject, None, None)))
                    else:
                        raise ValueError("Subject required for direct graph queries")
                        
                    return {"results": [(str(s), str(p), str(o)) for s, p, o in results]}
        except Exception as e:
            self.logger.error(f"Failed to query knowledge graph for agent {self.agent_id}: {str(e)}")
            raise 