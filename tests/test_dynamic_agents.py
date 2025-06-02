import pytest
import asyncio
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry
from agents.core.supervisor_agent import SupervisorAgent

class TestAgent(BaseAgent):
    """Test agent for dynamic instantiation tests."""
    
    def __init__(self, agent_id: str, agent_type: str = "test", capabilities=None, config=None):
        super().__init__(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities or {
                Capability(CapabilityType.TASK_EXECUTION)
            },
            config=config
        )
        
    async def process_message(self, message: AgentMessage) -> AgentMessage:
        return AgentMessage(
            sender=self.agent_id,
            recipient=message.sender,
            content={"status": "processed"},
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: dict) -> None:
        pass
        
    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

@pytest.fixture
async def setup():
    """Set up test environment."""
    registry = AgentRegistry()
    knowledge_graph = Graph()
    factory = AgentFactory(registry, knowledge_graph)
    
    # Register test agent template
    await factory.register_agent_template(
        "test",
        TestAgent,
        {CapabilityType.TASK_EXECUTION}
    )
    
    return registry, knowledge_graph, factory

@pytest.mark.asyncio
async def test_agent_creation(setup):
    """Test creating new agent instances."""
    registry, knowledge_graph, factory = await setup
    
    # Create a new agent
    agent = await factory.create_agent("test")
    assert agent is not None
    assert agent.agent_type == "test"
    assert agent.agent_id.startswith("test_")
    
    # Verify agent is registered
    registered_agent = await registry.get_agent(agent.agent_id)
    assert registered_agent is not None
    assert registered_agent.agent_id == agent.agent_id
    
    # Verify knowledge graph updates
    agent_uri = URIRef(f"agent:{agent.agent_id}")
    assert (agent_uri, RDF.type, URIRef("agent_type:test")) in knowledge_graph

@pytest.mark.asyncio
async def test_role_delegation(setup):
    """Test delegating new roles to agents."""
    registry, knowledge_graph, factory = await setup
    
    # Create initial agent
    agent = await factory.create_agent("test")
    
    # Register new role template
    await factory.register_agent_template(
        "processor",
        TestAgent,
        {CapabilityType.DATA_PROCESSING}
    )
    
    # Delegate new role
    await factory.delegate_role(
        agent.agent_id,
        "processor",
        {Capability(CapabilityType.DATA_PROCESSING)}
    )
    
    # Verify role change
    updated_agent = await registry.get_agent(agent.agent_id)
    assert updated_agent.agent_type == "processor"
    
    # Verify capabilities
    capabilities = await updated_agent.capabilities
    capability_types = {cap.type for cap in capabilities}
    assert CapabilityType.DATA_PROCESSING in capability_types
    
    # Verify knowledge graph updates
    agent_uri = URIRef(f"agent:{agent.agent_id}")
    assert (agent_uri, URIRef("agent:hasRole"), URIRef("role:processor")) in knowledge_graph

@pytest.mark.asyncio
async def test_agent_scaling(setup):
    """Test scaling agent instances."""
    registry, knowledge_graph, factory = await setup
    
    # Scale to 3 agents
    new_agents = await factory.scale_agents("test", 3)
    assert len(new_agents) == 3
    
    # Verify all agents are registered
    for agent in new_agents:
        registered_agent = await registry.get_agent(agent.agent_id)
        assert registered_agent is not None
        
    # Scale down to 1 agent
    remaining_agents = await factory.scale_agents("test", 1)
    assert len(remaining_agents) == 1
    
    # Verify excess agents are unregistered
    agent_count = len([
        a for a in registry.agents.values()
        if a.agent_type == "test"
    ])
    assert agent_count == 1

@pytest.mark.asyncio
async def test_supervisor_agent(setup):
    """Test supervisor agent functionality."""
    registry, knowledge_graph, factory = await setup
    
    # Create supervisor agent
    supervisor = SupervisorAgent(
        "supervisor_1",
        registry,
        knowledge_graph,
        {"workload_threshold": 2, "monitoring_interval": 1}
    )
    await supervisor.initialize()
    
    # Create some test agents
    await factory.scale_agents("test", 2)
    
    # Simulate workload
    for agent in registry.agents.values():
        if agent.agent_type == "test":
            await agent.update_status(AgentStatus.BUSY)
    
    # Wait for monitoring cycle
    await asyncio.sleep(2)
    
    # Verify auto-scaling
    agent_count = len([
        a for a in registry.agents.values()
        if a.agent_type == "test"
    ])
    assert agent_count > 2  # Should have scaled up
    
    # Test role change request
    message = AgentMessage(
        sender="test_agent",
        recipient="supervisor_1",
        content={
            "agent_id": list(registry.agents.keys())[0],
            "new_role": "processor"
        },
        message_type="role_change_request"
    )
    
    response = await supervisor.process_message(message)
    assert response.message_type == "role_change_response"
    assert "error" not in response.content
    
    # Cleanup
    await supervisor.cleanup()

@pytest.mark.asyncio
async def test_workload_monitoring(setup):
    """Test workload monitoring functionality."""
    registry, knowledge_graph, factory = await setup
    
    # Create initial agents
    await factory.scale_agents("test", 2)
    
    # Monitor workload
    workload = await factory.monitor_workload()
    assert "test" in workload
    assert workload["test"] == 0  # Initially idle
    
    # Set agents to busy
    for agent in registry.agents.values():
        if agent.agent_type == "test":
            await agent.update_status(AgentStatus.BUSY)
    
    # Check updated workload
    workload = await factory.monitor_workload()
    assert workload["test"] == 2  # Both agents busy
    
    # Test auto-scaling
    await factory.auto_scale(workload_threshold=1)
    
    # Verify new agents were created
    agent_count = len([
        a for a in registry.agents.values()
        if a.agent_type == "test"
    ])
    assert agent_count > 2  # Should have scaled up 