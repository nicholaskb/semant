import pytest
from tests.utils.test_agents import TestAgent
from agents.core.agent_message import AgentMessage

@pytest.mark.asyncio
async def test_test_agent_initialization():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={})
    assert agent.agent_id == "test_agent"
    assert agent.agent_type == "test"
    capabilities = await agent.capabilities
    assert capabilities == set()
    assert agent.default_response == {'status': 'processed'}

@pytest.mark.asyncio
async def test_test_agent_process_message():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={"status": "success"})
    message = AgentMessage(sender="sender", recipient="test_agent", content="Hello", timestamp="2023-01-01T00:00:00Z", message_type="request")
    response = await agent.process_message(message)
    assert response.sender == "test_agent"
    assert response.recipient == "sender"
    assert response.content == {"status": "success"}
    assert response.timestamp == "2023-01-01T00:00:00Z"
    assert response.message_type == "response"
    assert len(agent.message_history) == 1
    assert agent.message_history[0] == message

@pytest.mark.asyncio
async def test_test_agent_update_knowledge_graph():
    agent = TestAgent(agent_id="test_agent", agent_type="test", capabilities=[], default_response={})
    update_data = {"key": "value"}
    await agent.update_knowledge_graph(update_data)
    assert len(agent.knowledge_graph_updates) == 1
    assert agent.knowledge_graph_updates[0] == update_data 