import pytest
import pytest_asyncio
from agents.domain.vertex_email_agent import VertexEmailAgent
from agents.core.base_agent import AgentMessage
from kg.models.graph_manager import KnowledgeGraphManager

@pytest_asyncio.fixture
async def vertex_agent():
    kg = KnowledgeGraphManager()
    agent = VertexEmailAgent()
    agent.knowledge_graph = kg
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_send_email(vertex_agent):
    message = AgentMessage(
        sender_id="tester",
        recipient_id=vertex_agent.agent_id,
        content={"recipient": "user@example.com", "subject": "Hi", "body": "Test"},
        timestamp=0.0,
        message_type="send_email",
    )
    response = await vertex_agent.process_message(message)
    assert response.message_type == "send_email_response"
    assert response.content["status"] == "sent"
    assert len(vertex_agent.sent_emails) == 1
    # Verify knowledge graph updated
    data = await vertex_agent.query_knowledge_graph({"sparql": "SELECT ?s WHERE {?s ?p ?o}"})
    assert data
