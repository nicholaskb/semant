import pytest
import asyncio
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from agents.core.base_agent import BaseAgent, AgentStatus, AgentMessage
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_factory import AgentFactory
from agents.core.agent_registry import AgentRegistry
from agents.core.supervisor_agent import SupervisorAgent
import pytest_asyncio
import time
from typing import Dict, Any, List, Set
from tests.utils.test_agents import TestCapabilityAgent
from kg.models.graph_manager import KnowledgeGraphManager

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
            sender_id=self.agent_id,
            recipient_id=message.sender,
            content={"status": "processed"},
            message_type="response"
        )
        
    async def update_knowledge_graph(self, update_data: dict) -> None:
        pass
        
    async def query_knowledge_graph(self, query: dict) -> dict:
        return {}

    async def _process_message_impl(self, message: AgentMessage) -> AgentMessage:
        return await self.process_message(message)

@pytest_asyncio.fixture
async def registry():
    """Create a fresh AgentRegistry for each test."""
    registry = AgentRegistry()
    await registry.initialize()
    return registry

@pytest_asyncio.fixture
async def knowledge_graph():
    """Create a fresh knowledge graph for each test."""
    graph = KnowledgeGraphManager()
    await graph.initialize()
    return graph

@pytest_asyncio.fixture
async def factory(registry, knowledge_graph):
    """Create a fresh AgentFactory for each test."""
    factory = AgentFactory(registry, knowledge_graph)
    await factory.initialize()
    return factory

@pytest_asyncio.fixture
async def test_agent(factory):
    """Create a test agent with mixed capability types."""
    capabilities = {
        Capability("custom_capability", "A custom capability"),
        CapabilityType.KNOWLEDGE_GRAPH,
        CapabilityType.MESSAGE_PROCESSING
    }
    agent = await factory.create_agent("test_agent", "test", capabilities)
    return agent

@pytest_asyncio.fixture
async def capability_agent(factory):
    """Create a capability tracking agent."""
    capabilities = {CapabilityType.KNOWLEDGE_GRAPH}
    agent = await factory.create_agent("capability_agent", "test", capabilities)
    return agent

@pytest.mark.asyncio
async def test_agent_initialization(test_agent):
    """Test agent initialization and capability handling."""
    assert test_agent.id == "test_agent"
    assert test_agent.type == "test"
    capabilities = await test_agent.get_capabilities()
    assert len(capabilities) == 3
    assert any(cap.type == "custom_capability" for cap in capabilities)
    assert any(cap.type == CapabilityType.KNOWLEDGE_GRAPH for cap in capabilities)
    assert any(cap.type == CapabilityType.MESSAGE_PROCESSING for cap in capabilities)

@pytest.mark.asyncio
async def test_capability_tracking(capability_agent):
    """Test capability tracking during message processing."""
    message = {"type": "test", "content": "test message"}
    response = await capability_agent.process_message(message)
    assert response is not None
    
    history = await capability_agent.get_capability_history()
    assert len(history) > 0
    assert history[0]["message"] == message
    assert CapabilityType.KNOWLEDGE_GRAPH in history[0]["capabilities"]

@pytest.mark.asyncio
async def test_knowledge_graph_operations(capability_agent):
    """Test knowledge graph operations with capability tracking."""
    # Test update
    update_data = {"subject": "test", "predicate": "is", "object": "working"}
    await capability_agent.update_knowledge_graph(update_data)
    
    # Test query
    query = {"subject": "test"}
    result = await capability_agent.query_knowledge_graph(query)
    assert result is not None
    
    # Verify capability history
    history = await capability_agent.get_capability_history()
    assert len(history) >= 2
    assert any(entry["type"] == "update" for entry in history)
    assert any(entry["type"] == "query" for entry in history)

@pytest.mark.asyncio
async def test_agent_creation(factory):
    """Test agent creation with different capability types."""
    # Create agent with single capability
    agent1 = await factory.create_agent("agent1", "test", {CapabilityType.KNOWLEDGE_GRAPH})
    assert agent1 is not None
    capabilities1 = await agent1.get_capabilities()
    assert len(capabilities1) == 1
    assert CapabilityType.KNOWLEDGE_GRAPH in capabilities1
    
    # Create agent with multiple capabilities
    capabilities2 = {
        CapabilityType.KNOWLEDGE_GRAPH,
        CapabilityType.MESSAGE_PROCESSING,
        Capability("custom", "Custom capability")
    }
    agent2 = await factory.create_agent("agent2", "test", capabilities2)
    assert agent2 is not None
    capabilities2_result = await agent2.get_capabilities()
    assert len(capabilities2_result) == 3

@pytest.mark.asyncio
async def test_role_delegation(factory):
    """Test role delegation between agents."""
    # Create supervisor agent
    supervisor = await factory.create_agent("supervisor")
    
    # Create worker agent
    worker = await factory.create_agent(
        "worker",
        "worker",
        {CapabilityType.KNOWLEDGE_GRAPH}
    )
    
    # Test delegation
    message = {
        "type": "delegate",
        "content": "Process this data",
        "target": "worker"
    }
    response = await supervisor.process_message(message)
    assert response is not None
    
    # Verify worker received the message
    worker_history = await worker.get_capability_history()
    assert len(worker_history) > 0
    assert worker_history[0]["message"]["content"] == "Process this data"

@pytest.mark.asyncio
async def test_agent_scaling(factory):
    """Test agent scaling and workload distribution."""
    # Create multiple worker agents
    workers = []
    for i in range(3):
        worker = await factory.create_agent(
            f"worker_{i}"
        )
        workers.append(worker)
    
    # Create supervisor
    supervisor = await factory.create_agent("supervisor")
    
    # Test workload distribution
    for i in range(5):
        message = {
            "type": "process",
            "content": f"Task {i}",
            "target": "any_worker"
        }
        response = await supervisor.process_message(message)
        assert response is not None
    
    # Verify workload distribution
    for worker in workers:
        history = await worker.get_capability_history()
        assert len(history) > 0

@pytest.mark.asyncio
async def test_supervisor_agent(factory):
    """Test supervisor agent functionality."""
    supervisor = await factory.create_agent("supervisor")
    
    # Test supervisor operations
    message = {
        "type": "supervise",
        "content": "Monitor system",
        "target": "all"
    }
    response = await supervisor.process_message(message)
    assert response is not None
    
    # Verify supervisor capabilities
    capabilities = await supervisor.get_capabilities()
    assert CapabilityType.MESSAGE_PROCESSING in capabilities

@pytest.mark.asyncio
async def test_workload_monitoring(factory):
    """Test workload monitoring and balancing."""
    # Create monitoring agent
    monitor = await factory.create_agent(
        "monitor",
        "monitor",
        {CapabilityType.MESSAGE_PROCESSING}
    )
    
    # Create workers
    workers = []
    for i in range(2):
        worker = await factory.create_agent(
            f"worker_{i}"
        )
        workers.append(worker)
    
    # Test monitoring
    message = {
        "type": "monitor",
        "content": "Check workload",
        "target": "all"
    }
    response = await monitor.process_message(message)
    assert response is not None
    
    # Verify monitoring results
    history = await monitor.get_capability_history()
    assert len(history) > 0
    assert history[0]["message"]["type"] == "monitor" 