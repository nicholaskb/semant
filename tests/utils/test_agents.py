from typing import Dict, Any, List, Optional, Set, Union
from agents.core.base_agent import BaseAgent, AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
import time
from datetime import datetime
from agents.core.capability_types import Capability, CapabilityType

class TestAgent(BaseAgent):
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
        
    @property
    def capabilities(self) -> Set[Capability]:
        """Get capabilities as a set."""
        return self._capabilities
        
    @capabilities.setter
    def capabilities(self, value: Union[Set[Capability], List[Capability]]):
        """Set capabilities, converting list to set if needed."""
        self._capabilities = set(value) if value else set()
        
    def get_capabilities_list(self) -> List[str]:
        """Get capabilities as a sorted list for external use."""
        return sorted(list(self._capabilities))
        
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
        """Process a message and track history."""
        self.message_history.append({
            "timestamp": time.time(),
            "sender": message.sender,
            "content": message.content
        })
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content=self.default_response,
            timestamp=time.time()
        )
        
    def get_message_history(self) -> List[Dict[str, Any]]:
        """Get the agent's message history."""
        return self.message_history
        
    async def update_knowledge_graph(self, update_data: Dict[str, Any]) -> None:
        """Track knowledge graph updates."""
        self.knowledge_graph_updates.append({
            "timestamp": time.time(),
            "data": update_data
        })
        
    async def query_knowledge_graph(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Track knowledge graph queries."""
        self.knowledge_graph_queries.append({
            "timestamp": time.time(),
            "query": query
        })
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

class MockAgent(TestAgent):
    """Mock agent for basic testing."""
    
    def __init__(self, agent_id: str = "test_agent"):
        super().__init__(
            agent_id=agent_id,
            agent_type="mock",
            capabilities={Capability(CapabilityType.DATA_PROCESSING, "1.0")},
            default_response={"status": "processed"}
        )

class ResearchTestAgent(TestAgent):
    """Test agent for research capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_research_agent",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="research",
            capabilities={"research", "reasoning"},
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

class DataProcessorTestAgent(TestAgent):
    """Test agent for data processing capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_data_processor",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="data_processing",
            capabilities={"data_processing"},
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

class SensorTestAgent(TestAgent):
    """Test agent for sensor data capabilities."""
    
    def __init__(
        self,
        agent_id: str = "test_sensor",
        dependencies: Optional[List[str]] = None
    ):
        super().__init__(
            agent_id=agent_id,
            agent_type="sensor",
            capabilities={"sensor_data"},
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