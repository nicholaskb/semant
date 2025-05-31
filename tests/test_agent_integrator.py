import pytest
import pytest_asyncio
import time
from agents.core.agent_integrator import AgentIntegrator
from agents.core.base_agent import AgentMessage
from tests.utils.test_agents import MockAgent
from kg.models.graph_manager import KnowledgeGraphManager

@pytest_asyncio.fixture
async def integrator():
    """Create an AgentIntegrator instance for testing."""
    kg = KnowledgeGraphManager()
    kg.initialize_namespaces()
    integrator = AgentIntegrator(kg)
    yield integrator
    # Clean up background tasks
    await integrator.registry.shutdown()

@pytest_asyncio.fixture
async def mock_agent():
    """Create a mock agent for testing."""
    agent = MockAgent()
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_register_agent(integrator, mock_agent):
    """Test registering an agent."""
    await integrator.register_agent(mock_agent)
    assert mock_agent.agent_id in integrator.agents
    assert mock_agent.knowledge_graph is not None
    assert mock_agent.capabilities == ["mock"]
    
    # Verify knowledge graph integration
    assert mock_agent.knowledge_graph == integrator.knowledge_graph
    assert isinstance(mock_agent.knowledge_graph, KnowledgeGraphManager)

@pytest.mark.asyncio
async def test_route_message(integrator, mock_agent):
    """Test routing a message to an agent."""
    await integrator.register_agent(mock_agent)
    message = AgentMessage(
        sender="sender",
        recipient="test_agent",
        content={
            "required_capability": "mock",
            "test": "data"
        },
        timestamp=time.time(),
        message_type="test"
    )
    response = await integrator.route_message(message)
    assert response.sender == "test_agent"
    assert response.content["status"] == "processed"
    assert len(mock_agent.get_message_history()) == 1
    assert mock_agent.get_message_history()[0] == message

@pytest.mark.asyncio
async def test_broadcast_message(integrator, mock_agent):
    """Test broadcasting a message to all agents."""
    await integrator.register_agent(mock_agent)
    message = AgentMessage(
        sender="sender",
        recipient="all",
        content={"test": "data"},
        timestamp=time.time(),
        message_type="test"
    )
    responses = await integrator.broadcast_message(message)
    assert len(responses) == 1
    assert responses[0].sender == "test_agent"
    assert responses[0].content["status"] == "processed"
    assert len(mock_agent.get_message_history()) == 1
    assert mock_agent.get_message_history()[0] == message

@pytest.mark.asyncio
async def test_get_agent_status(integrator, mock_agent):
    """Test getting agent status."""
    await integrator.register_agent(mock_agent)
    status = await integrator.get_agent_status("test_agent")
    assert status["agent_id"] == "test_agent"
    assert status["agent_type"] == "mock"
    assert status["knowledge_graph_connected"] is True
    assert status["capabilities"] == ["mock"]

@pytest.mark.asyncio
async def test_get_all_agent_statuses(integrator, mock_agent):
    """Test getting status of all agents."""
    await integrator.register_agent(mock_agent)
    statuses = await integrator.get_all_agent_statuses()
    assert "test_agent" in statuses
    assert statuses["test_agent"]["agent_type"] == "mock"
    assert statuses["test_agent"]["capabilities"] == ["mock"]

@pytest.mark.asyncio
async def test_knowledge_graph_updates(integrator, mock_agent):
    """Test knowledge graph updates through agent."""
    await integrator.register_agent(mock_agent)
    update_data = {
        "subject": "test_subject",
        "predicate": "test_predicate",
        "object": "test_object"
    }
    await mock_agent.update_knowledge_graph(update_data)
    assert len(mock_agent.get_knowledge_graph_updates()) == 1
    assert mock_agent.get_knowledge_graph_updates()[0] == update_data
    
    # Verify the update was applied to the shared knowledge graph
    query = {"sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"}
    results = await integrator.knowledge_graph.query_graph(query["sparql"])
    assert len(results) > 0
    assert any(
        result["s"] == "test_subject" and 
        result["p"] == "test_predicate" and 
        result["o"] == "test_object"
        for result in results
    )

@pytest.mark.asyncio
async def test_knowledge_graph_queries(integrator, mock_agent):
    """Test knowledge graph queries through agent."""
    await integrator.register_agent(mock_agent)
    query = {"sparql": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"}
    result = await mock_agent.query_knowledge_graph(query)
    assert len(mock_agent.get_knowledge_graph_queries()) == 1
    assert mock_agent.get_knowledge_graph_queries()[0] == query 