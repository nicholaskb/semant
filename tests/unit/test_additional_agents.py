import pytest
import pytest_asyncio

from agents.domain.diary_agent import DiaryAgent
from agents.domain.simple_agents import FinanceAgent, CoachingAgent, IntelligenceAgent, DeveloperAgent
from agents.core.base_agent import AgentMessage
from tests.utils.test_agents import BaseTestAgent, TestAgent
from agents.core.capability_types import CapabilityType


@pytest_asyncio.fixture
async def diary_agent():
    agent = DiaryAgent()
    await agent.initialize()
    return agent


@pytest_asyncio.fixture
async def test_agents():
    """Create test instances of simple agents."""
    agents = {
        "finance": TestAgent(
            agent_id="finance_agent",
            agent_type="finance",
            capabilities=[CapabilityType.CODE_REVIEW],
            default_response={"status": "finance_processed", "result": "Financial analysis complete"}
        ),
        "coaching": TestAgent(
            agent_id="coaching_agent",
            agent_type="coaching",
            capabilities=[CapabilityType.CODE_REVIEW],
            default_response={"status": "coaching_processed", "result": "Coaching session complete"}
        ),
        "intelligence": TestAgent(
            agent_id="intelligence_agent",
            agent_type="intelligence",
            capabilities=[CapabilityType.CODE_REVIEW],
            default_response={"status": "intelligence_processed", "result": "Intelligence analysis complete"}
        ),
        "developer": TestAgent(
            agent_id="developer_agent",
            agent_type="developer",
            capabilities=[CapabilityType.CODE_REVIEW],
            default_response={"status": "development_processed", "result": "Development task complete"}
        )
    }
    for agent in agents.values():
        await agent.initialize()
    return agents


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
async def test_diary_agent(diary_agent):
    """Test diary agent functionality."""
    message = AgentMessage(
        sender="test_sender",
        recipient=diary_agent.agent_id,
        content={"entry": "Test diary entry"},
        timestamp=0.0,
        message_type="add_entry"
    )
    response = await diary_agent.process_message(message)
    assert response.message_type == "add_entry_response"
    assert "status" in response.content


@pytest.mark.asyncio
async def test_simple_agents_response(test_agents):
    """Test simple agents response handling."""
    for agent_id, agent in test_agents.items():
        message = AgentMessage(
            sender="tester",
            recipient=agent.agent_id,
            content={},
            timestamp=0.0,
            message_type="any"
        )
        response = await agent.process_message(message)
        assert response.message_type == "response"
        assert "status" in response.content
        assert "result" in response.content
        assert len(agent.get_message_history()) == 1
        assert agent.get_message_history()[0] == message


@pytest.mark.asyncio
async def test_simple_agents_knowledge_graph(test_agents):
    """Test simple agents knowledge graph operations."""
    for agent in test_agents.values():
        # Test update
        update_data = {
            "subject": "test_subject",
            "predicate": "test_predicate",
            "object": "test_object"
        }
        await agent.update_knowledge_graph(update_data)
        assert len(agent.get_knowledge_graph_updates()) == 1
        assert agent.get_knowledge_graph_updates()[0] == update_data
        
        # Test query
        query = {"sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"}
        result = await agent.query_knowledge_graph(query)
        assert len(agent.get_knowledge_graph_queries()) == 1
        assert agent.get_knowledge_graph_queries()[0] == query
