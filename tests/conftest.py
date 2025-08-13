import pytest
import pytest_asyncio
import time
from agents.core.agent_factory import AgentFactory
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from rdflib import Graph
from tests.utils.test_agents import BaseTestAgent

class TestAgent(BaseTestAgent):
    """Base test agent implementation."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "test",
        capabilities: set[Capability] = None,
        default_response: dict[str, any] = None
    ):
        """Initialize test agent."""
        if not capabilities:
            capabilities = {
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
                Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else capabilities,
            default_response=default_response
        )
        self._initialized = False
        self._message_history = []
        self._knowledge_graph_updates = []
        self._should_fail = False
        self._max_fails = 0
        self._fail_count = 0
        
    async def get_status(self) -> dict[str, any]:
        """Get agent status."""
        if not self._initialized:
            await self.initialize()
            
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": await self.get_capabilities(),
            "message_count": len(self._message_history),
            "knowledge_graph_updates": len(self._knowledge_graph_updates)
        }

class TestCapabilityAgent(TestAgent):
    """Test agent with capability management."""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str = "capability",
        capabilities: set[Capability] = None,
        config: dict[str, any] = None,
        default_response: dict[str, any] = None,
        knowledge_graph = None
    ):
        default_capabilities = {
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.TASK_EXECUTION, "1.0"),
            Capability(CapabilityType.CAPABILITY_MANAGEMENT, "1.0"),
            Capability(CapabilityType.MONITORING, "1.0"),
            Capability(CapabilityType.SUPERVISION, "1.0")
        }
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=set(capabilities) if capabilities else default_capabilities,
            default_response=default_response
        )
        self._capability_requests: list[dict[str, any]] = []
        self._capability_history: list[dict[str, any]] = []

    async def request_capability(self, capability: Capability) -> bool:
        """Request a new capability."""
        if not self._initialized:
            await self.initialize()
            
        request = {
            "capability": capability,
            "timestamp": time.time(),
            "status": "pending"
        }
        self._capability_requests.append(request)
        self._capability_history.append(request)
        
        # Return success
        return True
        
    def get_pending_requests(self) -> list[dict[str, any]]:
        """Get pending capability requests."""
        return [r for r in self._capability_requests if r["status"] == "pending"]
        
    async def get_capability_requests(self) -> list[Capability]:
        """Get capability requests - compatibility method for tests."""
        pending = self.get_pending_requests()
        return [request["capability"] for request in pending]

@pytest_asyncio.fixture
async def agent_factory():
    """Create an agent factory and register test agents."""
    factory = AgentFactory()
    await factory.initialize()
    
    # Register test agent templates
    await factory.register_agent_template("test_agent", TestAgent)
    await factory.register_agent_template("capability_agent", TestCapabilityAgent)
    
    yield factory
    
    # Cleanup
    await factory.cleanup()

@pytest_asyncio.fixture
async def agent_registry():
    """Create an agent registry instance for testing."""
    registry = AgentRegistry()
    await registry.initialize()
    yield registry
    await registry.cleanup()

@pytest_asyncio.fixture
async def test_agents(agent_factory):
    """Create a variety of test agents."""
    agents = {
        "worker": await agent_factory.create_agent("test_agent", "worker_1"),
        "monitor": await agent_factory.create_agent("capability_agent", "monitor_1"),
        "supervisor": await agent_factory.create_agent("capability_agent", "supervisor_1"),
    }
    return agents
