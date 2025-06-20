import pytest
from tests.utils.test_agents import TestAgent
from agents.core.message_types import AgentMessage
from datetime import datetime
from agents.core.capability_types import Capability, CapabilityType, CapabilitySet

@pytest.mark.asyncio
async def test_test_agent_initialization():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={})
    await agent.initialize()
    assert agent.agent_id == "test_agent"
    assert agent.agent_type == "test"
    capabilities = await agent.get_capabilities()
    assert isinstance(capabilities, CapabilitySet)
    assert len(capabilities) == 2  # Default capabilities

@pytest.mark.asyncio
async def test_test_agent_process_message():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={"status": "success"})
    await agent.initialize()
    message = {
        "sender_id": "sender",
        "recipient_id": "test_agent",
        "content": "Hello",
        "timestamp": datetime.fromisoformat("2023-01-01T00:00:00"),
        "message_type": "request"
    }
    response = await agent.process_message(message)
    assert response["sender_id"] == "test_agent"
    assert response["recipient_id"] == "sender"
    assert response["content"] == {"status": "success"}
    assert response["message_type"] == "response"

@pytest.mark.asyncio
async def test_test_agent_update_knowledge_graph():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={})
    await agent.initialize()
    update_data = {"key": "value"}
    await agent.update_knowledge_graph(update_data)
    updates = agent.get_knowledge_graph_updates()
    assert len(updates) == 1
    assert updates[0]["data"] == update_data 