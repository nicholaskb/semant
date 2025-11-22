import pytest
import pytest_asyncio
import time
from agents.core.agent_integrator import AgentIntegrator
from agents.core.base_agent import AgentMessage
from tests.utils.test_agents import MockAgent
from kg.models.graph_manager import KnowledgeGraphManager
from agents.core.capability_types import Capability, CapabilityType

@pytest_asyncio.fixture
async def integrator():
    """Create an AgentIntegrator instance for testing."""
    kg = KnowledgeGraphManager()
    await kg.initialize()
    integrator = AgentIntegrator(kg)
    await integrator.initialize()
    yield integrator
    # Clean up resources
    await integrator.registry.cleanup()
    await integrator.registry.shutdown()
    await kg.cleanup()

@pytest_asyncio.fixture
async def mock_agent():
    """Create a mock agent for testing with at least one capability."""
    capabilities = {Capability(CapabilityType.DATA_PROCESSING, "1.0")}
    agent = MockAgent(agent_id="test_agent", capabilities=capabilities)
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_register_agent(integrator, mock_agent):
    """Test registering an agent."""
    await integrator.register_agent(mock_agent)
    assert mock_agent.agent_id in integrator.agents
    assert mock_agent.knowledge_graph is not None
    capabilities = await mock_agent.capabilities
    assert capabilities == {Capability(CapabilityType.DATA_PROCESSING, "1.0")}
    
    # Verify knowledge graph integration
    assert mock_agent.knowledge_graph == integrator.knowledge_graph
    assert isinstance(mock_agent.knowledge_graph, KnowledgeGraphManager)

@pytest.mark.asyncio
async def test_route_message(integrator, mock_agent):
    """Test routing a message to an agent."""
    # Initialize agent first
    await mock_agent.initialize()
    
    # Register agent with explicit capabilities
    await integrator.register_agent(mock_agent)
    
    # Verify capabilities are registered
    capabilities = await mock_agent.capabilities
    assert capabilities == {Capability(CapabilityType.DATA_PROCESSING, "1.0")}
    
    # Create and send a test message
    message = AgentMessage(
        sender_id="sender",
        recipient_id="test_agent",
        content={
            "required_capability": CapabilityType.DATA_PROCESSING,
            "test": "data"
        },
        timestamp=time.time(),
        message_type="test"
    )
    
    # Route the message
    responses = await integrator.route_message(message)
    
    # Verify responses
    assert isinstance(responses, list)
    assert len(responses) > 0
    assert responses[0].sender == "test_agent"
    assert responses[0].recipient == "sender"
    assert responses[0].content == {"status": "processed"}
    assert responses[0].message_type == "response"
    
    # Verify message was processed
    message_history = mock_agent.get_message_history()
    assert len(message_history) == 1
    assert message_history[0] == message

@pytest.mark.asyncio
async def test_broadcast_message(integrator, mock_agent):
    """Test broadcasting a message to all agents."""
    await integrator.register_agent(mock_agent)
    message = AgentMessage(
        sender_id="sender",
        recipient_id="all",
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
    capabilities = await mock_agent.capabilities
    assert status["capabilities"] == list(capabilities)

@pytest.mark.asyncio
async def test_get_all_agent_statuses(integrator, mock_agent):
    """Test getting status of all agents."""
    await integrator.register_agent(mock_agent)
    statuses = await integrator.get_all_agent_statuses()
    assert "test_agent" in statuses
    assert statuses["test_agent"]["agent_type"] == "mock"
    capabilities = await mock_agent.capabilities
    assert statuses["test_agent"]["capabilities"] == list(capabilities)

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
    updates = mock_agent.get_knowledge_graph_updates()
    assert len(updates) == 1
    assert updates[0]["data"] == update_data
    assert "timestamp" in updates[0]
    
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
    queries = mock_agent.get_knowledge_graph_queries()
    assert len(queries) == 1
    assert queries[0]["query"] == query
    assert "timestamp" in queries[0]

@pytest.mark.asyncio
async def test_process_message_called_during_routing(integrator, mock_agent):
    """Test that process_message is called when routing messages."""
    await integrator.register_agent(mock_agent)
    
    # Clear any existing message history
    mock_agent._message_history.clear()
    
    # Create and send a test message
    message = AgentMessage(
        sender_id="sender",
        recipient_id="test_agent",
        content={"test": "data"},
        timestamp=time.time(),
        message_type="test"
    )
    
    # Route the message
    response = await integrator.route_message(message)
    
    # Verify process_message was called
    message_history = mock_agent.get_message_history()
    assert len(message_history) == 1
    assert message_history[0] == message
    
    # Verify response
    assert response.sender == "test_agent"
    assert response.recipient == "sender"
    assert response.content == {"status": "processed"}
    assert response.message_type == "response" 