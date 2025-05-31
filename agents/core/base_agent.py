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

class AgentMessage:
    """Represents a message between agents."""
    
    def __init__(
        self,
        sender: str,
        recipient: str,
        content: Dict[str, Any],
        timestamp: Optional[float] = None,
        message_type: str = "message"
    ):
        self.id = str(uuid.uuid4())
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.timestamp = timestamp or time.time()
        self.message_type = message_type

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "base",
        capabilities: Optional[Set[Capability]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self._capabilities = CapabilitySet()
        if capabilities:
            for capability in capabilities:
                self._capabilities.add(capability)
        self.config: Dict[str, Any] = config or {}
        self.knowledge_graph = None  # Will be set during initialization
        self.logger = logger.bind(agent_id=agent_id, agent_type=agent_type)
        self.diary: List[Dict[str, Any]] = []  # Each entry: {timestamp, message, [optional] details}
        self.status = AgentStatus.IDLE
        self._lock = asyncio.Lock()
        
    @property
    async def capabilities(self) -> Set[Capability]:
        """Get capabilities as a set."""
        return await self._capabilities.get_all()
        
    async def add_capability(self, capability: Capability) -> None:
        """Add a capability to the agent."""
        await self._capabilities.add(capability)
        
    async def remove_capability(self, capability: Capability) -> None:
        """Remove a capability from the agent."""
        await self._capabilities.remove(capability)
        
    async def has_capability(self, capability_type: CapabilityType) -> bool:
        """Check if the agent has a specific capability type."""
        return await self._capabilities.has_capability(capability_type)
        
    async def get_capability(self, capability_type: CapabilityType) -> Optional[Capability]:
        """Get a specific capability by type."""
        return await self._capabilities.get_capability(capability_type)
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent and its resources."""
        pass
    
    @abstractmethod
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a response."""
        pass
    
    @abstractmethod
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph with new information."""
        pass
    
    @abstractmethod
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph for information."""
        pass
    
    async def send_message(self, recipient: str, content: Dict[str, Any], 
                          message_type: str = "default") -> None:
        """Send a message to another agent."""
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            content=content,
            timestamp=time.time(),
            message_type=message_type
        )
        # Implementation will be added when we set up the message bus
        
    def log_activity(self, activity: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log agent activity with structured data."""
        self.logger.info(activity, extra=details or {})
        
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle errors in a standardized way."""
        self.logger.error(f"Error occurred: {str(error)}", extra=context)
        # Additional error handling logic can be added here 

    def write_diary(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Write a diary entry with a timestamp and optional details. Also add to the knowledge graph if available."""
        entry = {
            "timestamp": time.time(),
            "message": message,
        }
        if details:
            entry["details"] = details
        self.diary.append(entry)
        # Add to knowledge graph if available
        if self.knowledge_graph is not None and hasattr(self.knowledge_graph, 'graph'):
            g = self.knowledge_graph.graph
            agent_uri = f"agent:{self.agent_id}"
            diary_bnode = BNode()
            g.add((URIRef(agent_uri), DM.hasDiaryEntry, diary_bnode))
            g.add((diary_bnode, DM.timestamp, Literal(entry["timestamp"])))
            g.add((diary_bnode, DM.message, Literal(entry["message"])))
            if details:
                g.add((diary_bnode, DM.details, Literal(str(details))))
    
    def read_diary(self) -> List[Dict[str, Any]]:
        """Return all diary entries."""
        return self.diary
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
        
    def update_config(self, key: str, value: Any) -> None:
        """Update a configuration value."""
        self.config[key] = value
        self.logger.info(f"Updated config: {key}={value}")
        
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task. Must be implemented by concrete agents."""
        pass
        
    async def update_status(self, status: AgentStatus) -> None:
        """Update agent status with lock protection."""
        async with self._lock:
            self.status = status
            self.logger.info(f"Status updated to {status}")
            
    async def get_status(self) -> AgentStatus:
        """Get current agent status."""
        async with self._lock:
            return self.status
            
    async def validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate if agent can handle the task."""
        required_capability = task.get('capability')
        if not required_capability:
            return False
            
        return await self.has_capability(required_capability)
        
    async def handle_error(self, error: Exception) -> None:
        """Handle errors during task execution."""
        self.logger.exception(f"Error in agent {self.agent_id}: {str(error)}")
        await self.update_status(AgentStatus.ERROR)
        
    async def reset(self) -> None:
        """Reset agent to initial state."""
        async with self._lock:
            self.status = AgentStatus.IDLE
            self.logger.info("Agent reset to IDLE state") 