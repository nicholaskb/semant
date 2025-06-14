from typing import Dict, Any, List, Optional, Set, Union
from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
import time
from datetime import datetime
from agents.core.capability_types import Capability, CapabilityType

class BaseTestAgent(BaseAgent):
    """Base test agent with message history tracking."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "test",
        capabilities: Optional[Set[Capability]] = None,
        default_response: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(agent_id, agent_type, capabilities)
        self.default_response = default_response or {"status": "processed"}
        self.dependencies = dependencies or []
        self.message_history: List[Dict[str, Any]] = []
        self.knowledge_graph_updates: List[Dict[str, Any]] = []
        self.knowledge_graph_queries: List[Dict[str, Any]] = []
        
    def get_capabilities_list(self) -> List[str]:
        """Get capabilities as a sorted list for external use."""
        # This helper can be used in tests if needed
        # Note: This is not async and should not be used in async registry logic
        return []
        
    async def initialize(self) -> None:
        """Initialize the test agent."""
        if not self.knowledge_graph:
            self.knowledge_graph = KnowledgeGraphManager()
            self.knowledge_graph.initialize_namespaces()
        await super().initialize()
        
    async def process(self, data: Dict) -> Dict:
        """Process data and track message history."""
        message = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "response": self.default_response
        }
        self.message_history.append(message)
        return self.default_response
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message and return a response."""
        self.message_history.append(message)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=self.default_response,
            timestamp=message.timestamp,
            message_type="response"
        )
        
    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get the agent's message history."""
        return self.message_history
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Track knowledge graph updates."""
        self.knowledge_graph_updates.append(update_data)
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Track knowledge graph queries."""
        self.knowledge_graph_queries.append(query)
        return {"result": "test_result"}
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get the knowledge graph updates."""
        return self.knowledge_graph_updates
        
    def get_knowledge_graph_queries(self) -> List[Dict[str, Any]]:
        """Get the knowledge graph queries."""
        return self.knowledge_graph_queries
        
    def clear_history(self) -> None:
        """Clear all history."""
        self.message_history.clear()
        self.knowledge_graph_updates.clear()
        self.knowledge_graph_queries.clear()

class TestAgent(BaseTestAgent):
    """Test agent for workflow testing with simplified interface."""
    
    def __init__(
        self,
        agent_id: str,
        capabilities: Optional[Union[Set[Capability], Set[str]]] = None,
        agent_type: str = "test",
        default_response: Optional[Dict] = None,
        dependencies: Optional[List[str]] = None
    ):
        # Convert string capabilities to Capability objects if needed
        if capabilities and isinstance(next(iter(capabilities)), str):
            capabilities = {Capability(CapabilityType(cap), "1.0") for cap in capabilities}
            
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            default_response=default_response,
            dependencies=dependencies
        )
        self.processed_messages: List[Dict[str, Any]] = []
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message and track it in processed_messages."""
        self.message_history.append(message)
        self.processed_messages.append({
            "timestamp": message.timestamp,
            "sender": message.sender,
            "content": message.content
        })
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=self.default_response,
            timestamp=message.timestamp,
            message_type="response"
        )

class MockAgent(BaseAgent):
    """Mock agent for testing."""
    
    def __init__(
        self,
        agent_id: str = "test_agent",
        agent_type: str = "mock",
        capabilities: Optional[Set[Capability]] = None,
        default_response: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, agent_type, capabilities)
        self._message_history: List[AgentMessage] = []
        self._knowledge_graph_updates: List[Dict[str, Any]] = []
        self._knowledge_graph_queries: List[Dict[str, Any]] = []
        self._default_response = default_response or {"status": "processed"}
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        """Process a message and return a response."""
        self._message_history.append(message)
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=self._default_response,
            timestamp=message.timestamp,
            message_type="response"
        )
        
    def get_message_history(self) -> List[AgentMessage]:
        """Get the message history."""
        return self._message_history
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Update the knowledge graph and log the update."""
        self._knowledge_graph_updates.append({
            'data': update_data,
            'timestamp': datetime.now().isoformat()
        })
        # Actually update the shared knowledge graph if available
        if self.knowledge_graph and all(k in update_data for k in ("subject", "predicate", "object")):
            await self.knowledge_graph.add_triple(
                update_data["subject"],
                update_data["predicate"],
                update_data["object"]
            )
        
    def get_knowledge_graph_updates(self) -> List[Dict[str, Any]]:
        """Get the knowledge graph updates."""
        return self._knowledge_graph_updates
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Query the knowledge graph."""
        self._knowledge_graph_queries.append({
            'query': query,
            'timestamp': datetime.now().isoformat()
        })
        return {"results": []}
        
    def get_knowledge_graph_queries(self) -> List[Dict[str, Any]]:
        """Get the knowledge graph queries."""
        return self._knowledge_graph_queries

class ResearchTestAgent(BaseTestAgent):
    """Test agent for research capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_research_agent",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="research",
            capabilities={
                Capability(CapabilityType.RESEARCH, "1.0"),
                Capability(CapabilityType.REASONING, "1.0")
            },
            dependencies=dependencies
        )
        
    async def process(self, data: Dict) -> Dict:
        """Process data with research-specific logic."""
        message = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "response": {
                "status": "researched",
                "findings": "Test research findings",
                "confidence": 0.95
            }
        }
        self.message_history.append(message)
        return message["response"]

class DataProcessorTestAgent(BaseTestAgent):
    """Test agent for data processing capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_data_processor",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="data_processing",
            capabilities={Capability(CapabilityType.DATA_PROCESSING, "1.0")},
            dependencies=dependencies
        )
        
    async def process(self, data: Dict) -> Dict:
        """Process data with data processing logic."""
        message = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "response": {
                "status": "processed",
                "result": "Processed data",
                "metrics": {"accuracy": 0.98}
            }
        }
        self.message_history.append(message)
        return message["response"]

class SensorTestAgent(BaseTestAgent):
    """Test agent for sensor data capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_sensor",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="sensor",
            capabilities={Capability(CapabilityType.SENSOR_DATA, "1.0")},
            dependencies=dependencies
        )
        
    async def process(self, data: Dict) -> Dict:
        """Process sensor data with anomaly detection."""
        reading = data.get("reading", 0.0)
        is_anomaly = reading > 90.0
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "response": {
                "status": "sensor_processed",
                "reading": reading,
                "anomaly": is_anomaly,
                "flag": "anomaly" if is_anomaly else "normal",
                "recommendation": "Check sensor calibration" if is_anomaly else "All normal"
            }
        }
        self.message_history.append(message)
        return message["response"] 