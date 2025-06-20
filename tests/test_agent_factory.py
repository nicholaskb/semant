import pytest
import pytest_asyncio
from agents.core.agent_factory import AgentFactory
from agents.core.capability_types import Capability, CapabilityType
from agents.core.agent_registry import AgentRegistry
from rdflib import Graph
from tests.utils.test_agents import TestAgent, TestCapabilityAgent

# Using the global agent_factory fixture from conftest.py which properly registers test agents

@pytest.mark.asyncio
async def test_create_agent(agent_factory):
    # Create test agent
    agent = await agent_factory.create_agent(
        "test_agent",
        "test_1",
        {Capability(CapabilityType.KNOWLEDGE_GRAPH, "1.0")}
    )
    
    assert agent is not None
    assert agent.agent_id == "test_1"
    capabilities = await agent.get_capabilities()
    assert len(capabilities) == 1
    assert any(c.type == CapabilityType.KNOWLEDGE_GRAPH for c in capabilities)

@pytest.mark.asyncio
async def test_create_capability_agent(agent_factory):
    # Create capability agent
    agent = await agent_factory.create_agent(
        "capability_agent",
        "cap_1",
        {Capability(CapabilityType.CAPABILITY_MANAGEMENT, "1.0")}
    )
    
    assert agent is not None
    assert agent.agent_id == "cap_1"
    capabilities = await agent.get_capabilities()
    assert len(capabilities) == 1
    assert any(c.type == CapabilityType.CAPABILITY_MANAGEMENT for c in capabilities)

@pytest.mark.asyncio
async def test_agent_initialization(agent_factory):
    # Create and initialize agent
    agent = await agent_factory.create_agent(
        "test_agent",
        "test_2",
        {Capability(CapabilityType.KNOWLEDGE_GRAPH, "1.0")}
    )
    
    await agent.initialize()
    status = await agent.get_status()
    assert status["agent_id"] == "test_2"
    assert len(status["capabilities"]) == 1

@pytest.mark.asyncio
async def test_agent_capability_management(agent_factory):
    # Create capability agent and test capability requests
    agent = await agent_factory.create_agent(
        "capability_agent",
        "cap_2",
        {Capability(CapabilityType.CAPABILITY_MANAGEMENT, "1.0")}
    )
    
    new_capability = Capability(CapabilityType.KNOWLEDGE_GRAPH, "1.0")
    success = await agent.request_capability(new_capability)
    assert success
    
    requests = await agent.get_capability_requests()
    assert len(requests) == 1
    assert any(c.type == CapabilityType.KNOWLEDGE_GRAPH for c in requests) 