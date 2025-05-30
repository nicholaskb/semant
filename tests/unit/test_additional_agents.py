import pytest
import pytest_asyncio

from agents.domain.diary_agent import DiaryAgent
from agents.domain.simple_agents import FinanceAgent, CoachingAgent, IntelligenceAgent, DeveloperAgent
from agents.core.base_agent import AgentMessage


@pytest_asyncio.fixture
async def diary_agent():
    agent = DiaryAgent()
    await agent.initialize()
    return agent


@pytest.mark.asyncio
async def test_diary_write_and_query(diary_agent):
    message = AgentMessage(
        sender="tester",
        recipient=diary_agent.agent_id,
        content={"entry": "Today I wrote tests."},
        timestamp=0.0,
        message_type="add_entry",
    )
    response = await diary_agent.process_message(message)
    assert response.message_type == "add_entry_response"

    query_msg = AgentMessage(
        sender="tester",
        recipient=diary_agent.agent_id,
        content={"query": "today"},
        timestamp=0.0,
        message_type="query_diary",
    )
    query_response = await diary_agent.process_message(query_msg)
    assert query_response.message_type == "query_diary_response"
    assert "Today I wrote tests." in query_response.content["results"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_cls",
    [FinanceAgent, CoachingAgent, IntelligenceAgent, DeveloperAgent],
)
async def test_simple_agents_response(agent_cls):
    agent = agent_cls()
    await agent.initialize()
    message = AgentMessage(
        sender="tester",
        recipient=agent.agent_id,
        content={},
        timestamp=0.0,
        message_type="any",
    )
    response = await agent.process_message(message)
    assert response.message_type == "response"
    assert "response" in response.content
