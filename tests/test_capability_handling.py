import pytest
import pytest_asyncio
from typing import Dict, Any, List, Set
from agents.core.base_agent import BaseAgent, AgentMessage
from agents.core.agent_registry import AgentRegistry
from tests.utils.test_agents import BaseTestAgent
from agents.core.capability_types import Capability, CapabilityType

@pytest_asyncio.fixture(scope="function")
async def registry():
    """Create a fresh AgentRegistry instance for each test."""
    registry = AgentRegistry()
    await registry._auto_discover_agents()
    return registry

@pytest_asyncio.fixture(scope="function")
async def test_agent():
    """Create a test agent with mixed capability types."""
    agent = BaseTestAgent(
        agent_id="test_agent",
        agent_type="test",
        capabilities={
            Capability(CapabilityType.CODE_REVIEW, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0"),
            Capability(CapabilityType.SENSOR_READING, "1.0")
        }
    )
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_capability_type_conversion():
    """Test that capabilities are properly handled."""
    # Test with multiple capabilities
    capabilities = {
        Capability(CapabilityType.CODE_REVIEW, "1.0"),
        Capability(CapabilityType.DATA_PROCESSING, "1.0"),
        Capability(CapabilityType.SENSOR_READING, "1.0")
    }
    agent1 = BaseTestAgent(
        agent_id="agent1",
        capabilities=capabilities
    )
    await agent1.initialize()
    agent_capabilities = await agent1.get_capabilities()
    assert isinstance(agent_capabilities, set)
    assert len(agent_capabilities) == 3
    assert all(isinstance(cap, Capability) for cap in agent_capabilities)
    
    # Test empty capabilities
    agent2 = BaseTestAgent(
        agent_id="agent2",
        capabilities=None
    )
    await agent2.initialize()
    agent_capabilities = await agent2.get_capabilities()
    assert isinstance(agent_capabilities, set)
    assert len(agent_capabilities) == 0

@pytest.mark.asyncio
async def test_capability_operations():
    """Test capability operations."""
    agent = BaseTestAgent(
        agent_id="test_agent",
        capabilities={
            Capability(CapabilityType.CODE_REVIEW, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0")
        }
    )
    await agent.initialize()
    
    # Test has_capability
    assert await agent.has_capability(CapabilityType.CODE_REVIEW)
    assert await agent.has_capability(CapabilityType.DATA_PROCESSING)
    assert not await agent.has_capability(CapabilityType.SENSOR_READING)
    
    # Test get_capability
    review_cap = await agent.get_capability(CapabilityType.CODE_REVIEW)
    assert isinstance(review_cap, Capability)
    assert review_cap.type == CapabilityType.CODE_REVIEW
    assert review_cap.version == "1.0"
    
    # Test add_capability
    new_cap = Capability(CapabilityType.SENSOR_READING, "1.0")
    await agent.add_capability(new_cap)
    assert await agent.has_capability(CapabilityType.SENSOR_READING)
    
    # Test remove_capability
    await agent.remove_capability(new_cap)
    assert not await agent.has_capability(CapabilityType.SENSOR_READING)

@pytest.mark.asyncio
async def test_registry_capability_handling(registry, test_agent):
    """Test capability handling in the registry."""
    # Register agent
    await registry.register_agent(test_agent, await test_agent.get_capabilities())
    
    # Test get_agent_capabilities
    capabilities = await registry.get_agent_capabilities(test_agent.agent_id)
    assert isinstance(capabilities, set)
    assert all(isinstance(cap, Capability) for cap in capabilities)
    assert len(capabilities) == 3
    
    # Test update with new capabilities
    new_capabilities = {
        Capability(CapabilityType.CODE_REVIEW, "2.0"),
        Capability(CapabilityType.DATA_PROCESSING, "2.0")
    }
    await registry.update_agent_capabilities(
        test_agent.agent_id,
        new_capabilities
    )
    updated_capabilities = await registry.get_agent_capabilities(test_agent.agent_id)
    assert len(updated_capabilities) == 2
    assert all(isinstance(cap, Capability) for cap in updated_capabilities)

@pytest.mark.asyncio
async def test_capability_consistency(registry):
    """Test that capabilities remain consistent across operations."""
    # Create agents with overlapping capabilities
    agent1 = BaseTestAgent(
        agent_id="agent1",
        capabilities={
            Capability(CapabilityType.CODE_REVIEW, "1.0"),
            Capability(CapabilityType.DATA_PROCESSING, "1.0")
        }
    )
    await agent1.initialize()
    
    agent2 = BaseTestAgent(
        agent_id="agent2",
        capabilities={
            Capability(CapabilityType.DATA_PROCESSING, "1.0"),
            Capability(CapabilityType.SENSOR_READING, "1.0")
        }
    )
    await agent2.initialize()
    
    # Register agents
    await registry.register_agent(agent1, await agent1.get_capabilities())
    await registry.register_agent(agent2, await agent2.get_capabilities())
    
    # Test capability-based lookup
    review_agents = await registry.get_agents_by_capability(CapabilityType.CODE_REVIEW)
    assert len(review_agents) == 1
    assert review_agents[0].agent_id == "agent1"
    
    data_processing_agents = await registry.get_agents_by_capability(CapabilityType.DATA_PROCESSING)
    assert len(data_processing_agents) == 2
    assert {a.agent_id for a in data_processing_agents} == {"agent1", "agent2"}
    
    # Test capability updates
    await registry.update_agent_capabilities(
        "agent1",
        {Capability(CapabilityType.CODE_REVIEW, "2.0")}
    )
    data_processing_agents = await registry.get_agents_by_capability(CapabilityType.DATA_PROCESSING)
    assert len(data_processing_agents) == 1
    assert data_processing_agents[0].agent_id == "agent2"

@pytest.mark.asyncio
async def test_capability_edge_cases(registry):
    """Test edge cases in capability handling."""
    agent = BaseTestAgent(
        agent_id="test_agent",
        capabilities={
            Capability(CapabilityType.CODE_REVIEW, "1.0"),
            Capability(CapabilityType.CODE_REVIEW, "1.0"),  # Duplicate capability
            Capability(CapabilityType.CODE_REVIEW, "1.0")   # Duplicate capability
        }
    )
    await agent.initialize()
    
    # Register agent
    await registry.register_agent(agent, await agent.get_capabilities())
    
    # Verify duplicates are removed
    capabilities = await registry.get_agent_capabilities(agent.agent_id)
    assert len(capabilities) == 1
    assert all(isinstance(cap, Capability) for cap in capabilities)
    
    # Test empty capability updates
    await registry.update_agent_capabilities(agent.agent_id, set())
    capabilities = await registry.get_agent_capabilities(agent.agent_id)
    assert len(capabilities) == 0

@pytest.mark.asyncio
async def test_capability_initialization():
    """Test that capabilities are properly initialized on agent creation."""
    # Create agent with initial capabilities
    initial_capabilities = {
        Capability(CapabilityType.TASK_EXECUTION, "1.0"),
        Capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY, "1.0")
    }
    
    agent = BaseTestAgent(
        agent_id="test_init_agent",
        capabilities=initial_capabilities
    )
    await agent.initialize()
    
    # Verify capabilities are available immediately
    capabilities = await agent.get_capabilities()
    assert len(capabilities) == 2
    assert all(cap in capabilities for cap in initial_capabilities)
    
    # Verify initialization state
    assert agent._is_initialized is True
    
    # Verify capability operations work
    assert await agent.has_capability(CapabilityType.TASK_EXECUTION)
    assert await agent.has_capability(CapabilityType.KNOWLEDGE_GRAPH_QUERY)
    
    # Test adding new capability
    new_capability = Capability(CapabilityType.KNOWLEDGE_GRAPH_UPDATE, "1.0")
    await agent.add_capability(new_capability)
    updated_capabilities = await agent.get_capabilities()
    assert len(updated_capabilities) == 3
    assert new_capability in updated_capabilities 