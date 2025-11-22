import pytest
import pytest_asyncio

from agents.domain.diary_agent import DiaryAgent
from agents.domain.simple_agents import FinanceAgent, CoachingAgent, IntelligenceAgent, DeveloperAgent
from agents.domain.knowledge_personas import (
    KnowledgeGraphConsultant,
    OpenAIKnowledgeGraphEngineer,
    KnowledgeGraphVPLead,
)
from agents.core.base_agent import AgentMessage
from tests.utils.test_agents import BaseTestAgent, TestAgent
from agents.core.capability_types import CapabilityType, Capability
from agents.domain.judge_agent import JudgeAgent
from datetime import datetime


@pytest_asyncio.fixture
async def diary_agent():
    agent = DiaryAgent(
        agent_id="test_diary",
        agent_type="diary",
        capabilities={
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.DIARY_MANAGEMENT, "1.0")
        }
    )
    await agent.initialize()
    return agent


@pytest_asyncio.fixture
async def test_agents():
    """Create test instances of simple agents."""
    agents = {
        "finance": TestAgent(
            agent_id="finance_agent",
            agent_type="finance",
            capabilities={
                Capability(CapabilityType.CODE_REVIEW, "1.0"),
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")
            },
            default_response={"status": "finance_processed", "result": "Financial analysis complete"}
        ),
        "coaching": TestAgent(
            agent_id="coaching_agent",
            agent_type="coaching",
            capabilities={
                Capability(CapabilityType.CODE_REVIEW, "1.0"),
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")
            },
            default_response={"status": "coaching_processed", "result": "Coaching session complete"}
        ),
        "intelligence": TestAgent(
            agent_id="intelligence_agent",
            agent_type="intelligence",
            capabilities={
                Capability(CapabilityType.CODE_REVIEW, "1.0"),
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")
            },
            default_response={"status": "intelligence_processed", "result": "Intelligence analysis complete"}
        ),
        "developer": TestAgent(
            agent_id="developer_agent",
            agent_type="developer",
            capabilities={
                Capability(CapabilityType.CODE_REVIEW, "1.0"),
                Capability(CapabilityType.MESSAGE_PROCESSING, "1.0")
            },
            default_response={"status": "development_processed", "result": "Development task complete"}
        )
    }
    for agent in agents.values():
        await agent.initialize()
    return agents


@pytest_asyncio.fixture
async def judge_agent():
    agent = JudgeAgent(
        agent_id="test_judge",
        agent_type="judge",
        capabilities={
            Capability(CapabilityType.MESSAGE_PROCESSING, "1.0"),
            Capability(CapabilityType.DECISION_MAKING, "1.0")
        }
    )
    await agent.initialize()
    return agent


@pytest.mark.asyncio
async def test_diary_write_and_query(diary_agent):
    message = AgentMessage(
        sender_id="tester",
        recipient_id=diary_agent.agent_id,
        content={"entry": "Today I wrote tests."},
        timestamp=0.0,
        message_type="add_entry",
    )
    response = await diary_agent.process_message(message)
    assert response.content["status"] == "success"

    query_msg = AgentMessage(
        sender_id="tester",
        recipient_id=diary_agent.agent_id,
        content={"query": "today"},
        timestamp=0.0,
        message_type="query_diary",
    )
    query_response = await diary_agent.process_message(query_msg)
    assert query_response.message_type == "query_diary_response"
    assert "Today I wrote tests." in str(query_response.content.get("results", []))


@pytest.mark.asyncio
async def test_diary_agent(diary_agent):
    """Test diary agent functionality."""
    message = AgentMessage(
        sender_id="test_sender",
        recipient_id=diary_agent.agent_id,
        content={"entry": "Test diary entry"},
        timestamp=0.0,
        message_type="add_entry"
    )
    response = await diary_agent.process_message(message)
    assert response.content["status"] == "success"


@pytest.mark.asyncio
async def test_judge_evaluates_email(judge_agent):
    message = AgentMessage(
        sender_id="tester",
        recipient_id=judge_agent.agent_id,
        content={"action": "evaluate", "data": "dummy"},
        timestamp=0.0,
        message_type="evaluate",
    )
    response = await judge_agent.process_message(message)
    assert response.content["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_cls",
    [
        FinanceAgent,
        CoachingAgent,
        IntelligenceAgent,
        DeveloperAgent,
        KnowledgeGraphConsultant,
        OpenAIKnowledgeGraphEngineer,
        KnowledgeGraphVPLead,
    ],
)
async def test_simple_agents_response(agent_cls):
    agent = agent_cls()
    await agent.initialize()
    message = AgentMessage(
        sender_id="tester",
        recipient_id=agent.agent_id,
        content={},
        timestamp=0.0,
        message_type="any",
    )
    response = await agent.process_message(message)
    assert response.message_type in ["response", "error"]
    assert "response" in response.content or "Error" in str(response.content)


@pytest.mark.asyncio
async def test_vp_lead_complex_query():
    agent = KnowledgeGraphVPLead()
    await agent.initialize()
    message = AgentMessage(
        sender_id="tester",
        recipient_id=agent.agent_id,
        content={"query": "How to model customers and orders?"},
        timestamp=0.0,
        message_type="complex_query",
    )
    response = await agent.process_message(message)
    assert response.message_type == "complex_query_response"
    assert "Distilled code" in response.content["summary"]


@pytest.mark.asyncio
async def test_simple_agents_response_with_test_agents(test_agents):
    """Test that simple agents respond correctly."""
    expected_responses = {
        "finance": "Financial analysis complete",
        "coaching": "Coaching session complete",
        "intelligence": "Intelligence analysis complete",
        "developer": "Development task complete"
    }
    
    for agent_id, agent in test_agents.items():
        message = AgentMessage(
            sender_id="tester",
            recipient_id=agent.agent_id,
            content={"test": "data"},
            timestamp=0.0,
            message_type="test",
        )
        response = await agent.process_message(message)
        assert response.content["status"].endswith("_processed")
        assert response.content["result"] == expected_responses[agent_id]


@pytest.mark.asyncio
async def test_simple_agents_knowledge_graph(test_agents):
    """Test that simple agents can update and query the knowledge graph."""
    for agent in test_agents.values():
        # Test update
        update_data = {"test": "data"}
        await agent.update_knowledge_graph(update_data)
        
        # Test query
        query = {"test": "query"}
        result = await agent.query_knowledge_graph(query)
        assert result is not None
