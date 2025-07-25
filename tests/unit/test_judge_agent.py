import pytest
import pytest_asyncio

from agents.domain.judge_agent import JudgeAgent
from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager
from agents.utils import AwaitableValue


@pytest_asyncio.fixture
async def setup_agents():
    kg = KnowledgeGraphManager()
    email_agent = VertexEmailAgent()
    judge = JudgeAgent(kg=kg)
    email_agent.knowledge_graph = kg
    judge.knowledge_graph = kg
    await email_agent.initialize()
    await judge.initialize()
    agents = email_agent, judge
    return AwaitableValue(agents)


@pytest.mark.asyncio
async def test_judge_evaluates_email(setup_agents):
    email_agent, judge = await setup_agents
    message = AgentMessage(
        sender_id="tester",
        recipient_id=email_agent.agent_id,
        content={"recipient": "user@example.com", "subject": "Hi", "body": "Test"},
        timestamp=0.0,
        message_type="send_email",
    )
    await email_agent.process_message(message)

    decision = await judge.evaluate_challenge("dummy")
    assert decision == "Approved"
    assert judge.diary
