from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from loguru import logger
import time

class AgentMessage(BaseModel):
    """Base message model for agent communication."""
    sender: str
    recipient: str
    content: Dict[str, Any]
    timestamp: float
    message_type: str
    metadata: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.knowledge_graph = None  # Will be set during initialization
        self.logger = logger.bind(agent_id=agent_id, agent_type=agent_type)
        
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